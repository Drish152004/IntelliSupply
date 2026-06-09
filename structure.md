IntelliSupply/
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── Dockerfile
├── docker-compose.yml
├── README.md
├── requirements.txt
├── pytest.ini
├── agentic_ai/
│   ├── README.md
│   ├── main.py
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── inventory_agent.py
│   │   ├── inventory_agent_loop.py
│   │   ├── logistics_agent.py
│   │   ├── logistics_agent_loop.py
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── cache_key_builder.py
│   │   ├── cache_service.py
│   │   ├── memory_cache.py
│   │   ├── prediction_cache_config.py
│   │   ├── prediction_cache_key_builder.py
│   │   └── ttl_config.py
│   ├── context/
│   │   ├── __init__.py
│   │   ├── clarification_manager.py
│   │   ├── context_node.py
│   │   ├── entity_extractor.py
│   │   ├── field_source_registry.py
│   │   ├── graph_resolver.py
│   │   ├── missing_field_detector.py
│   │   ├── payload_builder.py
│   │   ├── query_completeness_checker.py
│   │   ├── resolver.py
│   │   └── task_requirements.py
│   ├── graph_retrieval/
│   │   ├── __init__.py
│   │   ├── cypher_generator.py
│   │   ├── entity_extractor.py
│   │   ├── graph_authorizer.py
│   │   ├── graph_node.py
│   │   ├── graph_retriever.py
│   │   ├── graph_service.py
│   │   └── result_mapper.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── graph_bridge.py
│   │   ├── inventory_tools.py
│   │   ├── llm_client.py
│   │   ├── logistics_tools.py
│   │   ├── ml_bridge.py
│   │   ├── ml_payload.py
│   │   ├── parameter_collector.py
│   │   └── sql_bridge.py
│   ├── orchestrator/
│   │   ├── cache_node.py
│   │   ├── executor.py
│   │   ├── graph.py
│   │   ├── intent.py
│   │   ├── intent_task_classifier.py
│   │   └── ...
│   ├── registry/
│   └── tests/
├── api/
│   ├── __init__.py
│   ├── copilot_router.py
│   └── schemas.py
├── backend/
│   ├── .gitkeep
│   ├── app.py
│   └── static/
│       └── style.css
├── config/
│   ├── __init__.py
│   ├── env.py
│   ├── ml_api.py
│   └── paths.py
├── FastAPI/
│   ├── .gitkeep
│   ├── bootstrap.py
│   ├── main.py
│   ├── README.md
│   ├── run.py
│   ├── dependencies/
│   ├── routers/
│   ├── schemas/
│   └── services/
├── frontend/
│   └── app/
│       ├── .env.example
│       ├── .gitignore
│       ├── components.json
│       ├── eslint.config.js
│       ├── index.html
│       ├── package-lock.json
│       ├── package.json
│       ├── postcss.config.js
│       ├── README.md
│       ├── tailwind.config.js
│       ├── tsconfig.app.json
│       ├── tsconfig.json
│       ├── tsconfig.node.json
│       ├── vite.config.ts
│       └── src/
│           ├── App.tsx
│           ├── index.css
│           ├── inventory.css
│           ├── main.tsx
│           ├── components/
│           ├── data/
│           ├── hooks/
│           └── lib/
├── ml/
│   ├── __init__.py
│   ├── ml_executor.py
│   ├── model_router.py
│   ├── validators.py
│   ├── adapters/
│   └── wrappers/
├── ml_services/
│   ├── __init__.py
│   ├── coordinate_mapping.py
│   ├── demand_forecasting/
│   ├── eta-prediction/
│   └── route_prediction/
├── notebooks/
│   └── route_prediction/
├── rag/
│   ├── __init__.py
│   ├── .gitkeep
│   ├── aura_graphdb/
│   │   ├── __init__.py
│   │   ├── aura_auth.py
│   │   ├── aura_clear.py
│   │   ├── aura_connection.py
│   │   ├── aura_constraints.py
│   │   ├── aura_courier.py
│   │   ├── aura_order.py
│   │   ├── aura_profiles.py
│   │   ├── aura_reseed.py
│   │   ├── aura_roles.py
│   │   ├── aura_route_cypher.py
│   │   ├── aura_route_prediction.py
│   │   ├── aura_route_queries.py
│   │   ├── aura_seed_logistics.py
│   │   ├── readme.md
│   │   ├── supabase_auth.py
│   │   └── supabase_connection.py
│   ├── graphdb/
│   │   ├── __init__.py
│   │   ├── clear_graph.py
│   │   ├── create_constraints.py
│   │   ├── cypher/
│   │   ├── graph_rag.py
│   │   ├── load_graph.py
│   │   ├── neo4j_connection.py
│   │   ├── README.md
│   │   └── supabase_connection.py
│   └── inventory/
│       ├── chatbot/
│       └── inventory_database/
└── tests/
    ├── conftest.py
    ├── test_copilot_api.py
    ├── test_demand_adapter.py
    ├── test_demand_wrapper.py
    ├── test_end_to_end_pipeline.py
    ├── test_eta_adapter.py
    ├── test_eta_wrapper.py
    ├── test_ml_execution_integration.py
    ├── test_ml_executor.py
    ├── test_response_formatter.py
    ├── test_route_adapter.py
    ├── test_route_wrapper.py
    └── components/
        ├── test_config_env.py
        ├── test_config_paths.py
        ├── test_coordinate_mapping.py
        ├── test_fastapi_health.py
        ├── test_fastapi_ml_endpoints.py
        ├── test_full_pipeline_demo.py
        ├── test_graph_bridge.py
        └── test_inventory_sql_bridge.py