import { Link } from 'react-router-dom'
import { IS_PUBLIC_SITE, publicAsset } from '@/lib/publicSite'

const FLOW = [
  {
    number: '01',
    title: 'Detect',
    description: 'Receive behavioral events, reports, and configured platform signals.',
  },
  {
    number: '02',
    title: 'Investigate',
    description: 'Assemble bounded evidence and calculate an explainable confidence score.',
  },
  {
    number: '03',
    title: 'Decide',
    description: 'Apply explicit policy thresholds and route sensitive cases to people.',
  },
  {
    number: '04',
    title: 'Act & audit',
    description: 'Coordinate platform actions, notifications, appeals, and durable audit records.',
  },
]

const CAPABILITIES = [
  {
    title: 'Event-driven analysis',
    description: 'Kinesis, EventBridge, and Lambda connect behavioral detection to investigation workflows.',
    accent: 'border-midnight/20 bg-midnight/5',
  },
  {
    title: 'Human review by design',
    description: 'Sensitive and uncertain cases enter a prioritized queue with reviewer wellbeing controls.',
    accent: 'border-kelp/25 bg-kelp/5',
  },
  {
    title: 'Reviewable policy',
    description: 'Configurable thresholds separate confidence scoring from enforcement authority.',
    accent: 'border-coral/25 bg-coral/5',
  },
  {
    title: 'Evidence and appeals',
    description: 'Evidence, decisions, notifications, and appeal records remain traceable through the workflow.',
    accent: 'border-mauve/30 bg-mauve/10',
  },
  {
    title: 'Replaceable integrations',
    description: 'Platform, partner-intelligence, image, and model adapters remain adopter-owned boundaries.',
    accent: 'border-sand/50 bg-pebble/40',
  },
  {
    title: 'Synthetic public demo',
    description: 'The published dashboard runs entirely in the browser and never contacts a private API.',
    accent: 'border-brand-300 bg-brand-50',
  },
]

const SERVICES = [
  ['Identity', 'Amazon Cognito'],
  ['API', 'Amazon API Gateway'],
  ['Events', 'Amazon Kinesis Data Streams'],
  ['Compute', 'AWS Lambda'],
  ['Workflow', 'AWS Step Functions'],
  ['State', 'Amazon DynamoDB'],
  ['Evidence', 'Amazon S3'],
  ['Alerts', 'Amazon SQS + SNS'],
  ['AI adapter', 'Amazon Bedrock (optional)'],
  ['Operations', 'Amazon CloudWatch + X-Ray'],
]

export function LandingPage() {
  const dashboardTarget = IS_PUBLIC_SITE ? '/app' : '/login'

  return (
    <div
      className="min-h-screen overflow-x-hidden bg-[#f7f4f8] text-gray-900"
      data-testid="canonical-landing"
    >
      <header className="border-b border-white/10 bg-[#17131c] text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <Link to="/" className="flex items-center gap-3" aria-label="SafetyAgent home">
            <img
              src={publicAsset('safetyagent-mark.svg')}
              alt=""
              className="h-10 w-10"
              data-testid="brand-mark"
            />
            <div>
              <div className="text-base font-semibold tracking-tight">SafetyAgent</div>
              <div className="text-xs text-white/55">Trust &amp; Safety Orchestration</div>
            </div>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-white/70 md:flex" aria-label="Public navigation">
            <Link className="transition hover:text-white" to="/architecture">Architecture</Link>
            <Link className="transition hover:text-white" to="/demo">Guided scenario</Link>
            <Link className="transition hover:text-white" to={dashboardTarget}>Dashboard</Link>
            <a
              className="transition hover:text-white"
              href="https://github.com/hk-775/trust-safety-orchestration-agent"
              rel="noreferrer"
              target="_blank"
            >
              GitHub
            </a>
          </nav>
          <Link
            to={dashboardTarget}
            className="rounded-lg border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15"
          >
            {IS_PUBLIC_SITE ? 'Open synthetic demo' : 'Open dashboard'}
          </Link>
        </div>
      </header>

      <main>
        <section className="relative isolate overflow-hidden bg-[#17131c] text-white">
          <div className="absolute inset-0 -z-10 opacity-70">
            <div className="absolute -left-24 top-10 h-80 w-80 rounded-full bg-midnight/60 blur-3xl" />
            <div className="absolute right-0 top-0 h-96 w-96 rounded-full bg-kelp/35 blur-3xl" />
            <div className="absolute bottom-0 left-1/2 h-56 w-96 -translate-x-1/2 rounded-full bg-aubergine/35 blur-3xl" />
          </div>
          <div className="mx-auto grid max-w-7xl gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:py-28">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-mauve/30 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-mist">
                Open AWS reference implementation
              </div>
              <h1 className="max-w-4xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
                Coordinate trust and safety decisions without hiding the human authority.
              </h1>
              <p className="mt-6 max-w-3xl text-lg leading-8 text-white/68">
                An event-driven sample for detecting policy risks, assembling evidence,
                applying explicit thresholds, and routing sensitive or uncertain cases to
                trained reviewers.
              </p>
              <div className="mt-9 flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/architecture"
                  data-testid="architecture-link"
                  className="inline-flex items-center justify-center rounded-lg bg-white px-5 py-3 text-sm font-semibold text-[#24142f] shadow-lg shadow-black/20 transition hover:-translate-y-0.5"
                >
                  Watch architecture walkthrough
                </Link>
                <Link
                  to="/demo"
                  data-testid="guided-demo-link"
                  className="inline-flex items-center justify-center rounded-lg border border-white/20 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Explore the guided scenario
                </Link>
                <Link
                  to={dashboardTarget}
                  data-testid="dashboard-link"
                  className="inline-flex items-center justify-center rounded-lg border border-kelp/70 bg-kelp/25 px-5 py-3 text-sm font-semibold text-white transition hover:bg-kelp/35"
                >
                  Open the dashboard
                </Link>
              </div>
              <p className="mt-5 text-xs leading-5 text-white/45">
                Reference/sample code only. The public experience uses synthetic data and
                performs no platform enforcement.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.07] p-5 shadow-2xl shadow-black/30 backdrop-blur">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-mist">
                    Illustrative orchestration
                  </div>
                  <div className="mt-1 text-sm text-white/55">Synthetic case TG-DEMO-1042</div>
                </div>
                <span className="rounded-full bg-kelp/25 px-3 py-1 text-xs font-semibold text-[#8bf1de]">
                  Human-review boundary
                </span>
              </div>
              <div className="space-y-3">
                {FLOW.map((item, index) => (
                  <div
                    key={item.number}
                    className="flex gap-4 rounded-xl border border-white/10 bg-black/10 p-4"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10 text-xs font-bold text-mist">
                      {item.number}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-semibold">{item.title}</h2>
                        {index === 2 && (
                          <span className="rounded bg-coral/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ffb9ad]">
                            policy route
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm leading-6 text-white/55">{item.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-gray-200/80 bg-white">
          <div className="mx-auto grid max-w-7xl grid-cols-2 divide-x divide-y divide-gray-200 px-5 sm:grid-cols-4 sm:divide-y-0 sm:px-8">
            {[
              ['4 stages', 'Detect to audit'],
              ['2 workflows', 'Investigation + bulk action'],
              ['Human first', 'Sensitive categories'],
              ['100% synthetic', 'Published experience'],
            ].map(([value, label]) => (
              <div key={label} className="px-4 py-6 text-center">
                <div className="text-xl font-bold text-midnight">{value}</div>
                <div className="mt-1 text-xs uppercase tracking-wider text-gray-500">{label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
          <div className="max-w-3xl">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-aubergine">
              Reviewable by construction
            </div>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Separate signal analysis from enforcement authority.
            </h2>
            <p className="mt-4 text-base leading-7 text-gray-600">
              The sample treats model output as one input to a policy workflow. Confidence,
              category sensitivity, precedent, and reviewer decisions remain explicit so an
              adopter can replace each boundary with its own lawful data, policies, and controls.
            </p>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((capability) => (
              <article
                key={capability.title}
                className={`rounded-2xl border p-6 ${capability.accent}`}
              >
                <h3 className="text-lg font-semibold text-gray-900">{capability.title}</h3>
                <p className="mt-3 text-sm leading-6 text-gray-600">{capability.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="bg-[#211929] text-white">
          <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
            <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-mist">
                  AWS reference architecture
                </div>
                <h2 className="mt-3 text-3xl font-bold tracking-tight">
                  Serverless orchestration with adopter-owned integrations.
                </h2>
                <p className="mt-4 text-sm leading-7 text-white/60">
                  The repository includes the SAM template, Step Functions definitions,
                  Python services, React operations dashboard, deployment automation, and
                  seeded development data.
                </p>
                <Link
                  to="/architecture"
                  className="mt-7 inline-flex rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-[#24142f]"
                >
                  Open interactive architecture
                </Link>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {SERVICES.map(([label, service]) => (
                  <div key={label} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-white/40">
                      {label}
                    </div>
                    <div className="mt-1 text-sm font-medium text-white/85">{service}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
          <div className="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm sm:p-12">
            <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-kelp">
                  Explore the artifacts
                </div>
                <h2 className="mt-3 text-3xl font-bold tracking-tight">
                  Follow the architecture, then operate the synthetic dashboard.
                </h2>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-gray-600">
                  Start with the narrated system path, walk through an illustrative scam case,
                  and inspect queues, evidence, policy configuration, and reviewer wellbeing
                  using browser-local sample records.
                </p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
                <Link to="/architecture" className="rounded-lg bg-midnight px-5 py-3 text-center text-sm font-semibold text-white">
                  Architecture
                </Link>
                <Link to="/demo" className="rounded-lg border border-gray-300 px-5 py-3 text-center text-sm font-semibold text-gray-800">
                  Guided scenario
                </Link>
                <Link to={dashboardTarget} className="rounded-lg border border-kelp/40 bg-kelp/5 px-5 py-3 text-center text-sm font-semibold text-kelp">
                  Synthetic dashboard
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-7 text-sm text-gray-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>SafetyAgent — Trust &amp; Safety Orchestration Agent</span>
          <span>Open reference implementation · MIT-0 · Synthetic demo data only</span>
        </div>
      </footer>
    </div>
  )
}
