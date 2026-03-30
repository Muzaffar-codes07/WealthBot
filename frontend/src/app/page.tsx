'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Brain,
  TrendingUp,
  Wallet,
  FileUp,
  Bell,
  ShieldCheck,
  Smartphone,
  RefreshCw,
  ArrowRight,
  Check,
  Sparkles,
} from 'lucide-react';
import { LandingNav, Footer } from '@/components/landing';

// ---------------------------------------------------------------------------
// Feature grid data
// ---------------------------------------------------------------------------
const features = [
  {
    icon: Brain,
    title: 'AI Categorization',
    description: 'ML classifies every transaction automatically with 95%+ accuracy using DistilBERT.',
  },
  {
    icon: TrendingUp,
    title: 'Spending Velocity',
    description: 'Track your burn rate vs. last month in real time. Spot leaks before they drain you.',
  },
  {
    icon: Wallet,
    title: 'Smart Budgeting',
    description: 'A daily safe-to-spend limit that adapts to your habits, income, and upcoming bills.',
  },
  {
    icon: FileUp,
    title: 'Bank Import',
    description: 'Upload CSV or PDF bank statements — transactions are parsed and categorized instantly.',
  },
  {
    icon: Bell,
    title: 'Subscription Radar',
    description: 'Spot recurring charges before they hit. Never forget a renewal again.',
  },
  {
    icon: ShieldCheck,
    title: 'Privacy First',
    description: 'Bank-grade encryption, zero data sharing, and PII masking in all logs.',
  },
];

// ---------------------------------------------------------------------------
// Pricing tiers
// ---------------------------------------------------------------------------
const tiers = [
  {
    name: 'Starter Plan',
    price: '₹0',
    period: '/mo',
    description: 'Perfect for students starting to track expenses.',
    features: [
      '50 transactions per month',
      'Basic AI categorization',
      'Daily safe-to-spend limit',
      'Manual transaction entry',
    ],
    cta: 'Get Started Free',
    highlighted: false,
  },
  {
    name: 'Pro Plan',
    price: '₹99',
    period: '/mo',
    description: 'Advanced tracking and smart budgeting for power users.',
    features: [
      'Unlimited transactions',
      'Spending velocity tracking',
      'Subscription radar alerts',
      'CSV & PDF bank import',
      'AI-powered fraud detection',
    ],
    cta: 'Subscribe Now',
    highlighted: true,
  },
  {
    name: 'Premium Plan',
    price: '₹299',
    period: '/mo',
    description: 'Full-suite analytics for serious savers.',
    features: [
      'Everything in Pro',
      'Priority AI chat assistant',
      'Advanced analytics & reports',
      'Family sharing (up to 4)',
      'API access for automation',
    ],
    cta: 'Subscribe Now',
    highlighted: false,
  },
];

// ---------------------------------------------------------------------------
// Trusted-by logos (placeholder names)
// ---------------------------------------------------------------------------
const trustedBy = ['FinStack', 'Polymath', 'EpicVentures', 'Acme Corp', 'BattleShift', 'EpikVibson'];

export default function LandingPage() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');

  return (
    <div className="min-h-screen bg-background-primary">
      <LandingNav />

      {/* ================================================================== */}
      {/* HERO                                                               */}
      {/* ================================================================== */}
      <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Instant Predictions
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary leading-tight tracking-tight">
              Revolutionizing Personal Finance with{' '}
              <span className="text-gradient-orange">Speed and Simplicity</span>
            </h1>

            <p className="mt-6 text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed">
              Say goodbye to lag pens and lost slips. Experience the future of personal finance,
              powered by AI prediction for instant daily safe-to-spend limits.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/login" className="btn-brand flex items-center gap-2">
                Get Started Free <ArrowRight className="w-4 h-4" />
              </Link>
              <a href="#features" className="btn-brand-outline flex items-center gap-2">
                See How It Works
              </a>
            </div>
          </div>

          {/* Floating glass cards */}
          <div className="mt-16 flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-8">
            {/* Card 1: Total Balance */}
            <div className="glass-card w-72 sm:w-80 animate-float relative">
              <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-brand-primary/10 blur-2xl pointer-events-none" />
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-full bg-brand-primary flex items-center justify-center">
                  <span className="text-white font-bold text-xs">W</span>
                </div>
                <span className="text-xs text-text-muted font-medium">WealthBot</span>
              </div>
              <p className="text-xs text-text-muted mb-1">Total Balance</p>
              <p className="text-2xl font-bold text-text-primary">₹86,320.25</p>
              <div className="flex items-center gap-4 mt-3 text-xs text-text-muted">
                <span>LAST 30 DAYS</span>
                <span className="text-semantic-success">+₹12,400</span>
              </div>
            </div>

            {/* Card 2: My Cards */}
            <div className="glass-card w-72 sm:w-80 animate-float relative" style={{ animationDelay: '1.5s' }}>
              <div className="absolute -bottom-4 -left-4 w-20 h-20 rounded-full bg-blue-500/10 blur-2xl pointer-events-none" />
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-full bg-brand-primary flex items-center justify-center">
                  <span className="text-white font-bold text-xs">W</span>
                </div>
                <span className="text-xs text-text-muted font-medium">WealthBot</span>
              </div>
              <p className="text-xs text-text-muted mb-1">My Cards</p>
              <p className="text-2xl font-bold text-text-primary">₹74,125.76</p>
              <div className="mt-3 flex gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-semantic-success/40" />
                <div className="h-1.5 w-8 rounded-full bg-brand-primary/40" />
                <div className="h-1.5 w-4 rounded-full bg-blue-500/40" />
              </div>
            </div>
          </div>

          {/* Trusted by */}
          <div className="mt-20 text-center">
            <p className="text-xs text-text-muted mb-6 uppercase tracking-wider">Trusted by</p>
            <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-12 opacity-40">
              {trustedBy.map((name) => (
                <span key={name} className="text-sm font-semibold text-text-secondary tracking-wide">
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/* FEATURE HIGHLIGHT                                                  */}
      {/* ================================================================== */}
      <section id="technology" className="py-20 sm:py-28 relative">
        <div className="absolute inset-0 bg-gradient-section pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-medium mb-4">
                From Days to Minutes
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-text-primary leading-tight">
                10x Faster<br />Transactions
              </h2>
              <p className="mt-4 text-text-secondary leading-relaxed">
                Reduce settlement time from 12 days to just 30 minutes. Experience unmatched
                speed powered by AI prediction technology.
              </p>
            </div>

            <div className="glass-card relative overflow-hidden">
              <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full glow-orange opacity-30 pointer-events-none" />
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-full bg-brand-primary flex items-center justify-center">
                  <span className="text-white font-bold text-sm">W</span>
                </div>
                <span className="text-sm text-text-muted font-medium">WealthBot</span>
              </div>
              <p className="text-xs text-text-muted mb-1">Total Balance</p>
              <p className="text-3xl font-bold text-text-primary">₹86,320.25</p>
              <div className="flex items-center gap-6 mt-4 text-xs text-text-muted">
                <span>LAST 30 DAYS <span className="text-semantic-success ml-1">+₹12,400</span></span>
                <span>USD/INR <span className="text-semantic-success ml-1">+3.2%</span></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/* DASHBOARD PREVIEW                                                  */}
      {/* ================================================================== */}
      <section className="py-20 sm:py-28 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-medium mb-4">
              From Days to Minutes
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-text-primary">
              Unlock the Power of<br />Smarter Transactions
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              By leveraging AI technology, advanced security, and user-friendly tools,
              we make financial tracking faster, cheaper, and more efficient.
            </p>
          </div>

          {/* Mock dashboard in glass card */}
          <div className="glass-card p-6 sm:p-8 relative overflow-hidden">
            <div className="absolute -top-20 right-0 w-60 h-60 rounded-full glow-orange opacity-20 pointer-events-none" />

            <div className="grid md:grid-cols-3 gap-6">
              {/* Left: Chart placeholder */}
              <div className="md:col-span-2 bg-background-secondary/60 rounded-xl p-4 border border-white/[0.04]">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-medium text-text-primary">Money Flow</h3>
                  <div className="flex gap-2">
                    {['Week', 'Month', 'Year'].map((label) => (
                      <span
                        key={label}
                        className={`text-xs px-2.5 py-1 rounded-md ${
                          label === 'Month'
                            ? 'bg-brand-primary/10 text-brand-primary'
                            : 'text-text-muted'
                        }`}
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                </div>
                {/* Chart bars */}
                <div className="flex items-end gap-2 h-32 mt-4">
                  {[40, 65, 50, 80, 55, 90, 70, 85, 60, 75, 95, 68].map((h, i) => (
                    <div key={i} className="flex-1 flex flex-col gap-1">
                      <div
                        className="rounded-t bg-semantic-success/60"
                        style={{ height: `${h}%` }}
                      />
                      <div
                        className="rounded-b bg-brand-primary/40"
                        style={{ height: `${Math.max(10, 100 - h)}%` }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Right: Stats */}
              <div className="space-y-4">
                <div className="bg-background-secondary/60 rounded-xl p-4 border border-white/[0.04]">
                  <p className="text-xs text-text-muted">My Cards</p>
                  <p className="text-xl font-bold text-text-primary mt-1">₹86,320.25</p>
                </div>
                <div className="bg-background-secondary/60 rounded-xl p-4 border border-white/[0.04]">
                  <p className="text-xs text-text-muted">Safe to Spend</p>
                  <p className="text-xl font-bold text-semantic-success mt-1">₹1,247</p>
                </div>
                <div className="bg-background-secondary/60 rounded-xl p-4 border border-white/[0.04]">
                  <p className="text-xs text-text-muted">Transaction History</p>
                  <div className="mt-3 space-y-2">
                    {[
                      { name: 'Swiggy', amount: '-₹189', color: 'text-text-primary' },
                      { name: 'Dad - UPI', amount: '+₹5,000', color: 'text-semantic-success' },
                      { name: 'Amazon', amount: '-₹1,299', color: 'text-text-primary' },
                    ].map((tx) => (
                      <div key={tx.name} className="flex items-center justify-between text-xs">
                        <span className="text-text-muted">{tx.name}</span>
                        <span className={`font-medium ${tx.color}`}>{tx.amount}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/* FEATURE GRID                                                       */}
      {/* ================================================================== */}
      <section id="features" className="py-20 sm:py-28 relative">
        <div className="absolute inset-0 bg-gradient-section pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div key={feature.title} className="glass-card-hover group">
                <div className="w-12 h-12 rounded-xl bg-brand-primary/10 flex items-center justify-center mb-4 group-hover:bg-brand-primary/20 transition-colors">
                  <feature.icon className="w-6 h-6 text-brand-primary" />
                </div>
                <h3 className="text-lg font-semibold text-text-primary mb-2">{feature.title}</h3>
                <p className="text-sm text-text-muted leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/* MOBILE SECTION                                                     */}
      {/* ================================================================== */}
      <section className="py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-medium mb-4">
                WealthBot for Mobile
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-text-primary leading-tight">
                Manage Your Transactions Anytime, Anywhere
              </h2>
              <p className="mt-4 text-text-secondary leading-relaxed">
                Experience the full power of WealthBot right from your smartphone. Our mobile app
                is designed to give you unmatched flexibility and convenience, making it the
                perfect tool for managing your finances on the go.
              </p>
              <div className="mt-8 space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center flex-shrink-0">
                    <Smartphone className="w-5 h-5 text-brand-primary" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-text-primary">Built for Mobility</h4>
                    <p className="text-sm text-text-muted mt-1">
                      Quick access to balances, spending velocity, and track activity, all in a few taps.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center flex-shrink-0">
                    <RefreshCw className="w-5 h-5 text-brand-primary" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-text-primary">Real-Time Updates</h4>
                    <p className="text-sm text-text-muted mt-1">
                      Get instant notification and real-time balance alerts for every transaction.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Phone mockup */}
            <div className="flex justify-center">
              <div className="glass-card w-64 sm:w-72 relative">
                <div className="absolute -top-6 -right-6 w-32 h-32 rounded-full bg-brand-primary/10 blur-2xl pointer-events-none" />
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-full bg-brand-primary flex items-center justify-center">
                    <span className="text-white font-bold text-xs">W</span>
                  </div>
                  <span className="text-sm font-medium text-text-primary">WealthBot</span>
                </div>
                <p className="text-xs text-text-muted mb-1">Safe to Spend</p>
                <p className="text-2xl font-bold text-semantic-success">₹1,247</p>
                <div className="mt-4 space-y-2">
                  {[
                    { name: 'Food & Dining', pct: 35, color: '#f59e0b' },
                    { name: 'Transport', pct: 20, color: '#3b82f6' },
                    { name: 'Shopping', pct: 25, color: '#ec4899' },
                    { name: 'Entertainment', pct: 10, color: '#8b5cf6' },
                  ].map((cat) => (
                    <div key={cat.name}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-text-muted">{cat.name}</span>
                        <span className="text-text-secondary">{cat.pct}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-background-hover">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${cat.pct}%`, backgroundColor: cat.color }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/* PRICING                                                            */}
      {/* ================================================================== */}
      <section id="pricing" className="py-20 sm:py-28 relative">
        <div className="absolute inset-0 bg-gradient-section pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-medium mb-4">
              Pricing
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-text-primary">
              Flexible Plans for Every Need
            </h2>
          </div>

          {/* Billing toggle */}
          <div className="flex items-center justify-center gap-2 mb-10">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                billingCycle === 'monthly'
                  ? 'bg-brand-primary text-white'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              Monthly billing
            </button>
            <button
              onClick={() => setBillingCycle('yearly')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                billingCycle === 'yearly'
                  ? 'bg-brand-primary text-white'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              Annual billing
            </button>
          </div>

          {/* Tier cards */}
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`glass-card relative ${
                  tier.highlighted ? 'border-brand-primary/40 ring-1 ring-brand-primary/20' : ''
                }`}
              >
                {tier.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-brand-primary text-white text-xs font-medium">
                    Most Popular
                  </div>
                )}

                <h3 className="text-lg font-semibold text-text-primary">{tier.name}</h3>
                <p className="text-sm text-text-muted mt-1">{tier.description}</p>

                <div className="mt-6 mb-6">
                  <span className="text-3xl font-bold text-text-primary">
                    {billingCycle === 'yearly' && tier.price !== '₹0'
                      ? `₹${Math.round(parseInt(tier.price.replace('₹', '')) * 10)}`
                      : tier.price}
                  </span>
                  <span className="text-text-muted text-sm">
                    {billingCycle === 'yearly' && tier.price !== '₹0' ? '/yr' : tier.period}
                  </span>
                </div>

                <Link
                  href="/login"
                  className={`block text-center w-full ${
                    tier.highlighted ? 'btn-brand' : 'btn-brand-outline'
                  }`}
                >
                  {tier.cta}
                </Link>

                <ul className="mt-6 space-y-3">
                  {tier.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2 text-sm text-text-secondary">
                      <Check className="w-4 h-4 text-semantic-success flex-shrink-0 mt-0.5" />
                      {feat}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/* CTA                                                                */}
      {/* ================================================================== */}
      <section className="py-20 sm:py-28 relative">
        <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary text-xs font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            Instant Payments
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary">
            Take Control of Your Payments
          </h2>
          <p className="mt-4 text-text-secondary max-w-xl mx-auto">
            Join thousands of students already using WealthBot to predict, track, and optimize their daily spending.
          </p>
          <Link href="/login" className="btn-brand inline-flex items-center gap-2 mt-8">
            Start for Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
