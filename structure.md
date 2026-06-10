Folder PATH listing
Volume serial number is 000000B6 16D6:237D
C:.
|   .env.example
|   .gitignore
|   ARCHITECTURE.md
|   docker-compose.yml
|   Dockerfile
|   pytest.ini
|   README.md
|   requirements.txt
|   structure.md
|   structure_tree.txt
|   
+---agentic_ai
|   |   main.py
|   |   README.md
|   |   
|   +---agents
|   |       base_agent.py
|   |       inventory_agent.py
|   |       inventory_agent_loop.py
|   |       logistics_agent.py
|   |       logistics_agent_loop.py
|   |       
|   +---cache
|   |       cache_key_builder.py
|   |       cache_service.py
|   |       memory_cache.py
|   |       prediction_cache_config.py
|   |       prediction_cache_key_builder.py
|   |       ttl_config.py
|   |       __init__.py
|   |       
|   +---context
|   |       clarification_manager.py
|   |       context_node.py
|   |       entity_extractor.py
|   |       field_source_registry.py
|   |       graph_resolver.py
|   |       missing_field_detector.py
|   |       payload_builder.py
|   |       query_completeness_checker.py
|   |       resolver.py
|   |       task_requirements.py
|   |       __init__.py
|   |       
|   +---graph_retrieval
|   |       cypher_generator.py
|   |       entity_extractor.py
|   |       graph_authorizer.py
|   |       graph_node.py
|   |       graph_retriever.py
|   |       graph_service.py
|   |       result_mapper.py
|   |       __init__.py
|   |       
|   +---integrations
|   |       graph_bridge.py
|   |       inventory_tools.py
|   |       llm_client.py
|   |       logistics_tools.py
|   |       ml_bridge.py
|   |       ml_payload.py
|   |       parameter_collector.py
|   |       sql_bridge.py
|   |       __init__.py
|   |       
|   +---orchestrator
|   |   |   cache_node.py
|   |   |   executor.py
|   |   |   graph.py
|   |   |   intent.py
|   |   |   intent_task_classifier.py
|   |   |   ml_node.py
|   |   |   prediction_cache_node.py
|   |   |   rbac_node.py
|   |   |   resource_rbac.py
|   |   |   response_formatter.py
|   |   |   router.py
|   |   |   state.py
|   |   |   
|   |   \---rbac
|   |           courier_identity.py
|   |           exceptions.py
|   |           permissions.py
|   |           rbac_service.py
|   |           role_mapper.py
|   |           session_context.py
|   |           __init__.py
|   |           
|   +---registry
|   |       agent_registry.py
|   |       
|   \---tests
|           test_cache.py
|           test_context.py
|           test_context_integration.py
|           test_courier_resource_rbac.py
|           test_graph_retrieval.py
|           test_graph_retrieval_integration.py
|           test_identity_propagation.py
|           test_intent.py
|           test_intent_task_classifier.py
|           test_ml_payload.py
|           test_ml_resource_rbac.py
|           test_multiturn_rbac.py
|           test_orchestrator.py
|           test_parameter_collector.py
|           test_prediction_cache.py
|           test_prediction_cache_integration.py
|           test_rbac.py
|           test_role_mapping.py
|           
+---api
|       copilot_router.py
|       schemas.py
|       __init__.py
|       
+---backend
|   |   .gitkeep
|   |   app.py
|   |   
|   \---static
|           style.css
|           
+---config
|       env.py
|       ml_api.py
|       paths.py
|       __init__.py
|       
+---FastAPI
|   |   .gitkeep
|   |   bootstrap.py
|   |   main.py
|   |   README.md
|   |   run.py
|   |   
|   +---dependencies
|   |       auth.py
|   |       __init__.py
|   |       
|   +---routers
|   |       auth.py
|   |       dashboard.py
|   |       demand_forecasting.py
|   |       eta_prediction.py
|   |       inventory.py
|   |       notifications.py
|   |       orders.py
|   |       route_prediction.py
|   |       users.py
|   |       __init__.py
|   |       
|   +---schemas
|   |       eta.py
|   |       orders.py
|   |       __init__.py
|   |       
|   \---services
|           dashboard.py
|           demand_forecasting.py
|           eta_prediction.py
|           inventory.py
|           notifications.py
|           orders.py
|           registry.py
|           route_prediction.py
|           __init__.py
|           
+---frontend
|   |   .gitkeep
|   |   
|   \---app
|       |   components.json
|       |   eslint.config.js
|       |   index.html
|       |   package-lock.json
|       |   package.json
|       |   postcss.config.js
|       |   README.md
|       |   tailwind.config.js
|       |   tsconfig.app.json
|       |   tsconfig.json
|       |   tsconfig.node.json
|       |   vite.config.ts
|       |   
|       \---src
|           |   App.tsx
|           |   index.css
|           |   inventory.css
|           |   main.tsx
|           |   
|           +---components
|           |   |   AICopilot.tsx
|           |   |   Navbar.tsx
|           |   |   ProtectedRoute.tsx
|           |   |   RouteMap.tsx
|           |   |   
|           |   \---ui
|           |           accordion.tsx
|           |           alert-dialog.tsx
|           |           alert.tsx
|           |           aspect-ratio.tsx
|           |           avatar.tsx
|           |           badge.tsx
|           |           breadcrumb.tsx
|           |           button-group.tsx
|           |           button.tsx
|           |           calendar.tsx
|           |           card.tsx
|           |           carousel.tsx
|           |           chart.tsx
|           |           checkbox.tsx
|           |           collapsible.tsx
|           |           command.tsx
|           |           context-menu.tsx
|           |           dialog.tsx
|           |           drawer.tsx
|           |           dropdown-menu.tsx
|           |           empty.tsx
|           |           field.tsx
|           |           form.tsx
|           |           hover-card.tsx
|           |           input-group.tsx
|           |           input-otp.tsx
|           |           input.tsx
|           |           item.tsx
|           |           kbd.tsx
|           |           label.tsx
|           |           menubar.tsx
|           |           navigation-menu.tsx
|           |           pagination.tsx
|           |           popover.tsx
|           |           progress.tsx
|           |           radio-group.tsx
|           |           resizable.tsx
|           |           scroll-area.tsx
|           |           select.tsx
|           |           separator.tsx
|           |           sheet.tsx
|           |           sidebar.tsx
|           |           skeleton.tsx
|           |           slider.tsx
|           |           sonner.tsx
|           |           spinner.tsx
|           |           switch.tsx
|           |           table.tsx
|           |           tabs.tsx
|           |           textarea.tsx
|           |           toggle-group.tsx
|           |           toggle.tsx
|           |           tooltip.tsx
|           |           
|           +---data
|           |       mockData.ts
|           |       
|           +---hooks
|           |       use-mobile.ts
|           |       
|           +---lib
|           |       api.ts
|           |       auth.tsx
|           |       utils.ts
|           |       
|           \---pages
|                   AdminAnalytics.tsx
|                   AdminUsers.tsx
|                   Home.tsx
|                   Inventory.tsx
|                   InventoryAnalytics.tsx
|                   Landing.tsx
|                   Login.tsx
|                   Notifications.tsx
|                   Overview.tsx
|                   ProductManagement.tsx
|                   Profile.tsx
|                   RegisterUser.tsx
|                   RouteIntelligence.tsx
|                   
+---ml
|   |   ml_executor.py
|   |   model_router.py
|   |   validators.py
|   |   __init__.py
|   |   
|   +---adapters
|   |       demand_adapter.py
|   |       eta_adapter.py
|   |       route_adapter.py
|   |       __init__.py
|   |       
|   \---wrappers
|           base.py
|           demand_wrapper.py
|           eta_wrapper.py
|           route_wrapper.py
|           __init__.py
|           
+---ml_services
|   |   .gitkeep
|   |   coordinate_mapping.py
|   |   __init__.py
|   |   
|   +---demand_forecasting
|   |   |   hf_client.py
|   |   |   inference.py
|   |   |   lade_demand.py
|   |   |   lade_weekly.py
|   |   |   MODEL_COMPATIBILITY.md
|   |   |   README.md
|   |   |   weekly_strategies.py
|   |   |   __init__.py
|   |   |   
|   |   +---full_pipeline
|   |   |       config.py
|   |   |       pipeline.py
|   |   |       run_demo.py
|   |   |       __init__.py
|   |   |       
|   |   +---hf_space
|   |   |   |   .gitattributes
|   |   |   |   Dockerfile
|   |   |   |   inference.py
|   |   |   |   README.md
|   |   |   |   
|   |   |   +---api
|   |   |   |       app.py
|   |   |   |       __init__.py
|   |   |   |       
|   |   |   \---models
|   |   |           lade_demand_forecaster.pkl
|   |   |           
|   |   \---models
|   |           bridge_test.pkl
|   |           forecast_next_4_weeks.csv
|   |           forecast_next_7_days.csv
|   |           lade_demand_forecaster.joblib
|   |           lade_demand_forecaster.meta.json
|   |           lade_demand_forecaster.pkl
|   |           lade_demand_forecaster_py312.pkl
|   |           lade_demand_forecaster_weekly.joblib
|   |           lade_demand_forecaster_weekly.meta.json
|   |           lade_demand_forecaster_weekly.pkl
|   |           model.skops
|   |           weekly_strategy.json
|   |           
|   +---eta-prediction
|   |   |   README.md
|   |   |   results.md
|   |   |   
|   |   +---api
|   |   |       main.py
|   |   |       schemas.py
|   |   |       __init__.py
|   |   |       
|   |   +---full_pipeline
|   |   |       feature_engineering.py
|   |   |       inference.py
|   |   |       preprocess.py
|   |   |       run_pipeline.py
|   |   |       training.py
|   |   |       __init__.py
|   |   |       
|   |   \---models
|   |           eta_lightgbm_model.pkl
|   |           
|   \---route_prediction
|       |   README.md
|       |   route_predictor.py
|       |   schemas.py
|       |   
|       \---full_pipeline
|           |   cluster_assigner.py
|           |   config.py
|           |   coordinates.py
|           |   courier_assigner.py
|           |   pipeline.py
|           |   run_demo.py
|           |   __init__.py
|           |   
|           \---data
|                   _generate_samples.py
|                   
+---notebooks
|   \---route_prediction
|           route_ranker.pkl
|           
+---rag
|   |   .gitkeep
|   |   __init__.py
|   |   
|   +---aura_graphdb
|   |       aura_auth.py
|   |       aura_clear.py
|   |       aura_connection.py
|   |       aura_constraints.py
|   |       aura_courier.py
|   |       aura_order.py
|   |       aura_profiles.py
|   |       aura_reseed.py
|   |       aura_roles.py
|   |       aura_route_cypher.py
|   |       aura_route_prediction.py
|   |       aura_route_queries.py
|   |       aura_seed_logistics.py
|   |       readme.md
|   |       supabase_auth.py
|   |       supabase_connection.py
|   |       __init__.py
|   |                 
|   +---inventory
|       \---chatbot
|               chatbot.py
|               create_tables.py
|               database.py
|               env_setup.py
|               load_data.py
|               models.py
|               query_executor.py
|               sql_generator.py
|               
\---tests
    |   conftest.py
    |   test_copilot_api.py
    |   test_demand_adapter.py
    |   test_demand_wrapper.py
    |   test_end_to_end_pipeline.py
    |   test_eta_adapter.py
    |   test_eta_wrapper.py
    |   test_ml_execution_integration.py
    |   test_ml_executor.py
    |   test_response_formatter.py
    |   test_route_adapter.py
    |   test_route_wrapper.py
    |   
    \---components
            test_config_env.py
            test_config_paths.py
            test_coordinate_mapping.py
            test_fastapi_health.py
            test_fastapi_ml_endpoints.py
            test_full_pipeline_demo.py
            test_graph_bridge.py
            test_inventory_sql_bridge.py
            
