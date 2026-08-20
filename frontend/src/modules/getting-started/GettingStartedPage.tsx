interface DeploymentStep {
  number: string
  title: string
  content?: string[]
  code?: string
  description?: string
  afterDescription?: string
  afterCode?: string
  note?: string
}

const steps: DeploymentStep[] = [
  {
    number: '1',
    title: 'Prerequisites',
    content: [
      'AWS CLI v2 configured with credentials',
      'AWS SAM CLI',
      'uv',
      'Node.js 20.19+, 22.12+, or a newer major release',
    ],
  },
  {
    number: '2',
    title: 'Clone the repository',
    code: `git clone https://github.com/hk-775/trust-safety-orchestration-agent.git
cd trust-safety-orchestration-agent`,
  },
  {
    number: '3',
    title: 'Install dependencies and build',
    code: './setup.sh',
  },
  {
    number: '4',
    title: 'Deploy a seeded development stack',
    description: 'The deployment script configures and publishes the frontend from stack outputs:',
    code: `read -r -s -p "Demo admin password: " DEMO_ADMIN_PASSWORD
printf '\\n'
export DEMO_ADMIN_PASSWORD
make quickstart
unset DEMO_ADMIN_PASSWORD`,
    note: 'The command prints the API, WebSocket, and CloudFront URLs after health checks pass.',
  },
  {
    number: '5',
    title: 'Deploy another environment',
    code: `make deploy \\
  ENVIRONMENT=staging \\
  STACK_NAME=trust-safety-orch-staging \\
  USE_REDIS=false`,
    note: 'Use DEPLOY_FRONTEND=false for a backend-only deployment.',
  },
  {
    number: '6',
    title: 'Access your app',
    description: 'Open the printed CloudFront URL. Seeded deployments create the admin demo user and dashboard records automatically.',
  },
]

function CodeBlock({ code }: { code: string }) {
  return (
    <pre className="mt-2 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
      <code>{code}</code>
    </pre>
  )
}

export function GettingStartedPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 p-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Getting Started</h1>
        <p className="mt-2 text-gray-600">
          Deploy the Trust &amp; Safety Orchestration Agent to your AWS account and get the dashboard running.
        </p>
      </div>

      <div className="space-y-6">
        {steps.map((step) => (
          <div key={step.number} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">
                {step.number}
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">{step.title}</h3>
                {step.description && (
                  <p className="mt-1 text-sm text-gray-600">{step.description}</p>
                )}
                {step.content && (
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-gray-700">
                    {step.content.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
                {step.code && <CodeBlock code={step.code} />}
                {step.afterDescription && (
                  <p className="mt-3 text-sm text-gray-600">{step.afterDescription}</p>
                )}
                {step.afterCode && <CodeBlock code={step.afterCode} />}
                {step.note && (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    <strong>Note:</strong> {step.note}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
        <h3 className="font-semibold text-amber-900">Production readiness</h3>
        <p className="mt-1 text-sm text-amber-800">
          Direct production deployment is disabled in this sample until upstream authentication and WebSocket authorization are implemented. Use <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs">prodtest</code> for a deletion-safe topology rehearsal.
        </p>
      </div>
    </div>
  )
}
