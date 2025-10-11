gov-contracts-ai/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/      # Endpoints
│   │   ├── core/     # Config, logging
│   │   ├── ml/       # ML inference
│   │   ├── ai/       # LLM integration
│   │   └── models/   # Database models
│   └── tests/        # Unit + integration tests
│
├── ml/               # ML development
│   ├── data/         # Raw, processed, features
│   ├── notebooks/    # EDA, experimentation
│   ├── src/          # Training code
│   └── pipelines/    # Prefect flows
│
├── frontend/         # Next.js app
│   ├── app/          # Pages (App Router)
│   ├── components/   # React components
│   └── lib/          # Utils, API client
│
├── infrastructure/   # IaC & deployment
│   ├── terraform/    # AWS resources
│   └── docker-compose.yml
│
├── docs/             # Documentation
│   ├── architecture.md
│   ├── api-docs.md
│   └── ml-methodology.md
│
└── scripts/          # Utility scripts
