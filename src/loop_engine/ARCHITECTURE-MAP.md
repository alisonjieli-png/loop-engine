ARCHITECTURE MAP: six top-level abstractions
  ontology/  (8 modules)
    artifacts, catalog, folders, loop_definition_record, loop_node, node, ontology_checks, records
  loop/  (39 modules)
    approval_state_store, approval_state_store_checks, atomic_primitives, intrinsic_kernel, capability_loops, canvas, spawned_runtime_port, spawned_task_checkpoint, spawned_task_state_store, spawned_task_state_store_checks, spawned_workspace_executor, spawned_workspace_executor_checks, delegation_checkpoint_checks, delegation_runtime, delegation_runtime_checks, effect_approval, kernel, kernel_runtime, loop_templates, lens, intelligence_loops, encapsulate, loop_capsule, loop_contract, loop_definition, loop_definition_checks, runtime_context, loop_doctrine, loop_profile_catalog, loop_profile_ontology, loop_role, loop_control, reactive_activation, reactive_contract_checks, reactive_contracts, reactive_outputs, recursive_loop, service_loop_envelope, spawned_practitioner
  strings/  (13 modules)
    ask_strategies, context, decision_schemas, frame, intelligence_strings, interrogation, knowledge, knowledge_state, notes, output_templates, prompt_fragments, question_engine, solution_shaping
  code_nodes/  (39 modules)
    ascii_views, ascii_views_checks, blueprint, campaign_runner, capture, context_seed, core_engine_proof, complex_task_benchmark, complex_task_native_evidence, complex_task_published_evidence, follow_up, housekeeping, kaggle_executor, live_run_demo, learning_bundle, guided_setup, logic_ast, universal_solve, loop_report, measurement, public_examples, guidance_ledger, run_analytics, run_playback, run_quality, runtime_contracts, self_improvement_loop, smoke_ladder, solve_runtime, solution_canvas, solution_canvas_checks, solution_compiler, solution_model_port, solution_graph, solution_graph_builder, solution_graph_checks, solution_graph_validation, solution_records, string_foundry
  core/  (118 modules)
    adaptive_practitioner, adaptive_practitioner_acceptance_checks, adaptive_practitioner_capabilities, adaptive_practitioner_checks, adaptive_practitioner_deterministic, adaptive_practitioner_planning, adaptive_practitioner_orientation, adaptive_practitioner_prompting, adaptive_practitioner_records, adaptive_practitioner_recovery, adaptive_practitioner_supervision, adaptive_practitioner_validation, adaptive_practitioner_verification, api_quality, asset_class, component_contracts, component_inventory, asset_lifecycle, brave_search, capability_directory, run_history, config, context_artifacts, context_catalog, context_classification, context_ontology, code_intelligence_assets, event_vocabulary, duckdb_catalog, external_harness, external_harness_adapters, external_harness_checks, facets, harness_intelligence_bridge, intelligence_layers, intelligence_query_contracts, intelligence_portfolio, intelligence_portfolio_checks, runtime_memory, user_feedback_intelligence, intelligence_registry, live_model_verification, live_text_scenarios, mcp_adapter, mcp_adapter_checks, mcp_sdk_transport, model_call, model_capabilities, model_gateway, model_response_text, model_routing_intelligence, model_routing_intelligence_checks, model_routing_records, model_routing_selector, ngram_benchmark, ngram_retrieval, otel_export, primitive_conformance, runtime_observer, runtime_settings, settings_loader, information_access, information_access_checks, reactive_output_store, reactive_output_store_checks, reactive_scheduler, reactive_scheduler_checks, reactive_worker, reactive_worker_checks, plugin_bundles, plugin_bundles_checks, development_planning, development_planning_checks, development_execution, development_execution_checks, development_governance, development_governance_checks, lifecycle_extensions, lifecycle_extensions_checks, software_tdd_skill_checks, model_routes, ollama_client, mistral_client, openrouter_client, provider_failover, provider_pinned, model_discovery, autoconfigure, custom_endpoint, generated_project, generated_project_artifact_validation, knowledge_loader, llm_work_packet, opencode_client, operating_profile, persistence, practitioner_context, reasoning_call, resolution, retrieval, skill_registry, solution_library, task_compile_model, task_fingerprint, store_serve, boundary_registry, boundary_runtime_checks, saas_routes, studio_operational_views, studio_server, workspace_backends, workspace_contracts, workspace_local, workspace_operation_checks, web_fetch, web_search, workspace_operations, workspace_optional
  catalog/  (7 modules)
    capabilities, composite, conformance, handshake, protocol, registry, query
    catalog.stores/  (5 modules)
      duckdb_files, duckdb_store, in_memory, package_jsonl, sqlite_store
  memory/  (1 modules)
    loop_integration
    memory.episodic/  (1 modules)
      record
    memory.lifecycle/  (1 modules)
      lifecycle
    memory.model/  (5 modules)
      identity, lifecycle, memory_type, reference, scope
    memory.procedural/  (1 modules)
      record
    memory.query/  (2 modules)
      query, receipts
    memory.semantic/  (1 modules)
      record
    memory.storage/  (5 modules)
      store, repository, learning_cycle, learning_cycle_checks, learning_records
    memory.working/  (1 modules)
      state
  generation/  (2 modules)
    expansion, operators
    generation.model/  (4 modules)
      campaign, dimensions, fragments, seeds
  templates/  (4 modules)
    compiler, intake, library, model
PUBLIC CORE ARCHITECTURE CAPABILITY GROUPS (3)
  Intelligence Search and Retrieval: intelligence_layers, retrieval, capability_directory
  Web Research: brave_search
  Custom Plugins: capability_directory, brave_search
All other core modules are internal runtime services, not peer public capability groups.
