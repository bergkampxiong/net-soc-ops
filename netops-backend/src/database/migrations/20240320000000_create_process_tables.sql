-- 流程定义表
CREATE TABLE process_definitions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    version INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, published, disabled
    nodes JSON NOT NULL, -- 节点配置
    edges JSON NOT NULL, -- 边配置
    variables JSON, -- 变量定义
    created_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(36) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

-- 流程实例表
CREATE TABLE process_instances (
    id VARCHAR(36) PRIMARY KEY,
    definition_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'running', -- running, completed, terminated, suspended, failed
    variables JSON, -- 实例变量
    current_node VARCHAR(36), -- 当前节点ID
    started_by VARCHAR(36) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    created_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(36) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    FOREIGN KEY (definition_id) REFERENCES process_definitions(id)
);

-- 节点执行历史表
CREATE TABLE node_execution_history (
    id VARCHAR(36) PRIMARY KEY,
    instance_id VARCHAR(36) NOT NULL,
    node_id VARCHAR(36) NOT NULL,
    node_name VARCHAR(100) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- running, completed, failed
    input_data JSON, -- 输入数据
    output_data JSON, -- 输出数据
    error_message TEXT, -- 错误信息
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES process_instances(id)
);

-- 边执行历史表
CREATE TABLE edge_execution_history (
    id VARCHAR(36) PRIMARY KEY,
    instance_id VARCHAR(36) NOT NULL,
    edge_id VARCHAR(36) NOT NULL,
    source_node_id VARCHAR(36) NOT NULL,
    target_node_id VARCHAR(36) NOT NULL,
    status VARCHAR(20) NOT NULL, -- completed, failed
    condition_result BOOLEAN, -- 条件结果
    error_message TEXT, -- 错误信息
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES process_instances(id)
);

-- 创建索引
CREATE INDEX idx_process_definitions_status ON process_definitions(status);
CREATE INDEX idx_process_definitions_created_by ON process_definitions(created_by);
CREATE INDEX idx_process_instances_definition_id ON process_instances(definition_id);
CREATE INDEX idx_process_instances_status ON process_instances(status);
CREATE INDEX idx_process_instances_started_by ON process_instances(started_by);
CREATE INDEX idx_node_execution_history_instance_id ON node_execution_history(instance_id);
CREATE INDEX idx_edge_execution_history_instance_id ON edge_execution_history(instance_id); 