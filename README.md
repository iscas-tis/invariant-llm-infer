# invariant-llm-infer

LLM-based invariant inference for C programs.

Repository: https://github.com/iscas-tis/invariant-llm-infer

## Quick Start

```bash
# Generate invariant with verification
PYTHONPATH=src python -m inv_assume.pipeline examples/nonlin_div_term_1.c --output results/test --config llm_config.json --verify
```

See [docs/quickstart.md](docs/quickstart.md) for detailed instructions.

## Features

- Loop invariant generation using LLM
- SeaHorn verification integration
- Two-stage generation strategy
- Multi-agent refinement pipeline
- MCP server for IDE integration