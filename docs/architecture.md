flowchart TD
    subgraph build["Build time — runs once before each Docker image build"]
        CSV["data/source/Resume.csv\n9 544 rows"]

        subgraph pipeline["scripts/prepare_dataset.py"]
            S1["Stage 1 — Load\nvalidate columns"]
            S2["Stage 2 — Sample\n2–3 CVs per job category\ncap at 50"]
            S3["Stage 3 — Injection check\nclassify_injection() on\ncareer_objective + skills + responsibilities"]
            S4["Stage 4 — Map columns\nskills · experience · education · summary\nno PII fields in schema"]
            S5["Stage 5 — Embed + index\ngemini-embedding-001 via LiteLLM\nChroma upsert"]
        end

        CSV --> S1 --> S2 --> S3 --> S4 --> S5

        S3 -->|"injection_detected"| EX
        S4 -->|"no_skills / parse_failed"| EX

        EX["data/exclusions.json\n1 excluded · 49 included"]
        POOL["data/pool/candidate_NNN.json\n49 files — zero PII"]
        CHROMA["data/chroma/\nchroma.sqlite3 — metadata + document text\n478bb9cb.../ — HNSW binary vectors\n49 docs · 768 dims · collection: candidates"]

        S4 --> POOL
        S5 --> CHROMA
    end

    subgraph libs["backend/src/lib — shared by build + runtime"]
        INJ["guardrails/injection.py\nclassify_injection()\n12 regex patterns"]
        LLM["llm/client.py\ncomplete() — gemini-2.5-flash + OpenAI fallback\nembed() — gemini-embedding-001"]
    end

    subgraph schemas["scripts/schemas.py"]
        SC["ParsedCandidate\nExperienceEntry · EducationEntry\nExclusionLog · ExclusionEntry\nExclusionReason"]
    end

    subgraph tests["Tests — 77 passing"]
        T1["backend/tests/guardrails/\ntest_injection.py\n46 unit tests\ninjection_payloads.jsonl — 17 fixtures"]
        T2["scripts/tests/\ntest_prepare_dataset.py\n31 integration tests\nLiteLLM mocked"]
    end

    subgraph config["Project config"]
        GI[".gitignore\ncovers .env · data/source/ · data/chroma/\n.venv · __pycache__ · caches"]
        PI["pytest.ini\ncache_dir → backend/.pytest_cache"]
        PYPROJ["backend/pyproject.toml\nuv · ruff · pytest config\ndeps: litellm · chromadb · pydantic · pandas"]
    end

    INJ -.->|"imported by"| pipeline
    LLM -.->|"imported by"| pipeline
    SC -.->|"imported by"| pipeline

    T1 -.->|"tests"| INJ
    T2 -.->|"tests"| pipeline
