"""
WealthBot DistilBERT Transaction Categorizer — Training Script
===============================================================
Fine-tunes a **DistilBERT** classification head to predict transaction
categories from ``merchant_name + " " + description`` text.

Strategy: freeze all DistilBERT base layers, train only the classification
head (transfer learning).  This keeps training fast (~5 min on Colab T4)
and the model small.

Designed to run standalone on **Google Colab (T4 GPU)** or locally (CPU).

Outputs
-------
- ``ml/models/categorizer.onnx``   — ONNX model for production inference
- ``ml/models/tokenizer/``          — saved HuggingFace tokenizer
- ``ml/models/label_encoder.json``  — category ↔ index mapping

Usage
-----
::

    # Local (from project root, venv activated)
    python -m ml.training.train_categorizer

    # Google Colab
    !pip install transformers torch onnxruntime pandas numpy
    # Upload synthetic_transactions.csv, then run this file
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import (  # type: ignore[attr-defined]
    DistilBertForSequenceClassification,
    DistilBertTokenizerFast,
    get_linear_schedule_with_warmup,
)

# =============================================================================
# Paths
# =============================================================================

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
CSV_PATH = Path(__file__).resolve().parent / "synthetic_transactions.csv"
ONNX_OUTPUT_PATH = MODELS_DIR / "categorizer.onnx"
TOKENIZER_OUTPUT_DIR = MODELS_DIR / "tokenizer"
LABEL_ENCODER_PATH = MODELS_DIR / "label_encoder.json"

# =============================================================================
# Constants
# =============================================================================

MAX_LENGTH = 64  # Token length — merchant + description fits in ~20 tokens
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 5e-4
WARMUP_RATIO = 0.1
BASE_MODEL = "distilbert-base-uncased"


# =============================================================================
# Data Preparation
# =============================================================================


def load_and_prepare_data() -> (
    tuple[list[str], list[int], list[str], list[int], dict[str, int], dict[int, str]]
):
    """Load transactions CSV and prepare text inputs + label mappings.

    Text input: ``merchant_name + " " + description``
    Label: integer-encoded ``category``

    Returns:
        (train_texts, train_labels, val_texts, val_labels,
         label2id, id2label)
    """
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} transactions from {CSV_PATH.name}")

    # Build text input from merchant + description
    df["text"] = (
        df["merchant_name"].fillna("").astype(str)
        + " "
        + df["description"].fillna("").astype(str)
    )

    # All categories (including Income, Savings, etc.)
    all_categories = sorted(df["category"].unique().tolist())
    label2id: dict[str, int] = {cat: idx for idx, cat in enumerate(all_categories)}
    id2label: dict[int, str] = {idx: cat for cat, idx in label2id.items()}
    n_labels = len(all_categories)

    print(f"Categories ({n_labels}): {all_categories}")

    df["label"] = df["category"].map(label2id)

    # Stratified-ish split: 80% train / 20% val, shuffled by user
    user_ids = df["user_id"].unique()
    rng = np.random.default_rng(42)
    rng.shuffle(user_ids)
    split_idx = int(len(user_ids) * 0.8)
    train_users = set(user_ids[:split_idx])

    train_df = df[df["user_id"].isin(train_users)].reset_index(drop=True)
    val_df = df[~df["user_id"].isin(train_users)].reset_index(drop=True)

    print(f"Train: {len(train_df):,}  |  Val: {len(val_df):,}")

    return (
        train_df["text"].tolist(),
        train_df["label"].tolist(),
        val_df["text"].tolist(),
        val_df["label"].tolist(),
        label2id,
        id2label,
    )


# =============================================================================
# Dataset
# =============================================================================


class TransactionDataset(Dataset):  # type: ignore[type-arg]
    """PyTorch dataset that tokenizes text on-the-fly."""

    def __init__(
        self,
        texts: list[str],
        labels: list[int],
        tokenizer: DistilBertTokenizerFast,
        max_length: int = MAX_LENGTH,
    ) -> None:
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        encoding: dict[str, Any] = self.tokenizer(
            self.texts[idx],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


# =============================================================================
# Model Setup
# =============================================================================


def create_model(
    n_labels: int,
    id2label: dict[int, str],
    label2id: dict[str, int],
    device: torch.device,
) -> DistilBertForSequenceClassification:
    """Load DistilBERT and freeze the base transformer layers.

    Only the classification head (pre_classifier + classifier + dropout)
    is trainable — transfer learning approach.

    Args:
        n_labels: Number of output classes.
        id2label: Index → category name mapping.
        label2id: Category name → index mapping.
        device: Compute device.

    Returns:
        Model with frozen base, moved to device.
    """
    model: DistilBertForSequenceClassification = (
        DistilBertForSequenceClassification.from_pretrained(
            BASE_MODEL,
            num_labels=n_labels,
            id2label=id2label,
            label2id=label2id,
        )
    )

    # Freeze all DistilBERT base layers — only train the classification head
    for param in model.distilbert.parameters():
        param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(
        f"Parameters: {total:,} total, {trainable:,} trainable "
        f"({100 * trainable / total:.1f}%)"
    )

    return model.to(device)  # type: ignore[no-any-return, arg-type]


# =============================================================================
# Training Loop
# =============================================================================


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,  # type: ignore[type-arg]
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    device: torch.device,
) -> tuple[float, float]:
    """Run one training epoch.

    Returns:
        (avg_loss, accuracy) for the epoch.
    """
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )

        loss = outputs.loss
        total_loss += loss.item() * input_ids.size(0)

        preds = outputs.logits.argmax(dim=-1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()

    avg_loss = total_loss / total
    accuracy = correct / total
    return avg_loss, accuracy


@torch.no_grad()
def evaluate_epoch(
    model: nn.Module,
    dataloader: DataLoader,  # type: ignore[type-arg]
    device: torch.device,
) -> tuple[float, float]:
    """Run one evaluation epoch.

    Returns:
        (avg_loss, accuracy) for the epoch.
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )

        total_loss += outputs.loss.item() * input_ids.size(0)
        preds = outputs.logits.argmax(dim=-1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    avg_loss = total_loss / total
    accuracy = correct / total
    return avg_loss, accuracy


def train(
    model: DistilBertForSequenceClassification,
    train_loader: DataLoader,  # type: ignore[type-arg]
    val_loader: DataLoader,  # type: ignore[type-arg]
    device: torch.device,
) -> DistilBertForSequenceClassification:
    """Full training loop with warmup schedule.

    Args:
        model: DistilBERT model (base frozen).
        train_loader: Training data loader.
        val_loader: Validation data loader.
        device: Compute device.

    Returns:
        The model with the best validation accuracy weights.
    """
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
        weight_decay=0.01,
    )

    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(  # type: ignore[no-untyped-call]
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    best_val_acc = 0.0
    best_state: dict[str, Any] = {}

    print(
        f"\nTraining for {EPOCHS} epochs "
        f"(batch={BATCH_SIZE}, lr={LEARNING_RATE}, warmup={warmup_steps})"
    )
    print("-" * 65)

    start = time.perf_counter()

    for epoch in range(1, EPOCHS + 1):
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, scheduler, device
        )
        val_loss, val_acc = evaluate_epoch(model, val_loader, device)

        marker = ""
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            marker = " ★"

        print(
            f"  Epoch {epoch:2d}/{EPOCHS}  "
            f"train_loss={train_loss:.4f}  train_acc={train_acc:.4f}  |  "
            f"val_loss={val_loss:.4f}  val_acc={val_acc:.4f}{marker}"
        )

    elapsed = time.perf_counter() - start
    print(
        f"\nTraining completed in {elapsed:.1f}s  "
        f"(best val accuracy: {best_val_acc:.4f})"
    )

    # Restore best weights
    if best_state:
        model.load_state_dict(best_state)

    return model


# =============================================================================
# ONNX Export
# =============================================================================


def export_onnx(
    model: DistilBertForSequenceClassification,
    tokenizer: DistilBertTokenizerFast,
) -> None:
    """Export the fine-tuned model to ONNX format.

    Args:
        model: Trained DistilBERT model.
        tokenizer: Tokenizer (used for dummy input).
    """
    model.eval()  # type: ignore[no-untyped-call]
    model = model.to("cpu")  # type: ignore[arg-type]

    dummy_text = "Swiggy Food purchase"
    dummy_input = tokenizer(
        dummy_text,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    input_ids = dummy_input["input_ids"]
    attention_mask = dummy_input["attention_mask"]

    print(f"\nExporting to ONNX → {ONNX_OUTPUT_PATH}")

    torch.onnx.export(
        model,
        (input_ids, attention_mask),
        str(ONNX_OUTPUT_PATH),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size"},
            "attention_mask": {0: "batch_size"},
            "logits": {0: "batch_size"},
        },
        opset_version=14,
        do_constant_folding=True,
    )

    # Verify ONNX output
    _verify_onnx(model, input_ids, attention_mask)

    print(f"ONNX model saved ({ONNX_OUTPUT_PATH.stat().st_size / 1024:.1f} KB)")


def _verify_onnx(
    model: nn.Module,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
) -> None:
    """Verify ONNX output matches PyTorch output."""
    import onnxruntime as ort

    session = ort.InferenceSession(str(ONNX_OUTPUT_PATH))

    with torch.no_grad():
        pt_logits = model(input_ids, attention_mask).logits.numpy()

    onnx_logits = session.run(
        None,
        {
            "input_ids": input_ids.numpy(),
            "attention_mask": attention_mask.numpy(),
        },
    )[0]

    max_diff = float(np.max(np.abs(pt_logits - onnx_logits)))
    print(f"ONNX verification — max abs diff: {max_diff:.6f}", end="")
    if max_diff < 0.01:
        print(" ✓")
    else:
        print(" ✗ (WARN: diff exceeds 0.01)")


# =============================================================================
# Save Artifacts
# =============================================================================


def save_tokenizer(tokenizer: DistilBertTokenizerFast) -> None:
    """Save tokenizer to disk for inference."""
    TOKENIZER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(str(TOKENIZER_OUTPUT_DIR))
    print(f"Tokenizer saved → {TOKENIZER_OUTPUT_DIR}")


def save_label_encoder(
    label2id: dict[str, int],
    id2label: dict[int, str],
) -> None:
    """Save label encoder mapping to JSON."""
    encoder = {
        "label2id": label2id,
        "id2label": {str(k): v for k, v in id2label.items()},
        "num_labels": len(label2id),
    }
    with open(LABEL_ENCODER_PATH, "w", encoding="utf-8") as f:
        json.dump(encoder, f, indent=2, ensure_ascii=False)
    print(f"Label encoder saved → {LABEL_ENCODER_PATH}")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run the full DistilBERT categorizer training pipeline."""
    print("=" * 60)
    print("WealthBot — DistilBERT Transaction Categorizer Training")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # --- Data ---
    (
        train_texts,
        train_labels,
        val_texts,
        val_labels,
        label2id,
        id2label,
    ) = load_and_prepare_data()

    # --- Tokenizer ---
    tokenizer: DistilBertTokenizerFast = DistilBertTokenizerFast.from_pretrained(
        BASE_MODEL
    )

    # --- Datasets & Loaders ---
    train_ds = TransactionDataset(train_texts, train_labels, tokenizer)
    val_ds = TransactionDataset(val_texts, val_labels, tokenizer)

    train_loader: DataLoader[Any] = DataLoader(
        train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0
    )
    val_loader: DataLoader[Any] = DataLoader(
        val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0
    )

    # --- Model ---
    model = create_model(len(label2id), id2label, label2id, device)

    # --- Train ---
    model = train(model, train_loader, val_loader, device)

    # --- Export ---
    export_onnx(model, tokenizer)
    save_tokenizer(tokenizer)
    save_label_encoder(label2id, id2label)

    print("\n✅ Training pipeline complete.")


if __name__ == "__main__":
    main()
