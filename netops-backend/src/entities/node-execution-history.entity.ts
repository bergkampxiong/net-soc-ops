import { Entity, Column, PrimaryColumn, CreateDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { ProcessInstance } from './process-instance.entity';

@Entity('node_execution_history')
export class NodeExecutionHistory {
  @PrimaryColumn('varchar', { length: 36 })
  id: string;

  @Column('varchar', { length: 36 })
  instance_id: string;

  @ManyToOne(() => ProcessInstance)
  @JoinColumn({ name: 'instance_id' })
  instance: ProcessInstance;

  @Column('varchar', { length: 36 })
  node_id: string;

  @Column('varchar', { length: 100 })
  node_name: string;

  @Column('varchar', { length: 50 })
  node_type: string;

  @Column('varchar', { length: 20 })
  status: 'running' | 'completed' | 'failed';

  @Column('json', { nullable: true })
  input_data: Record<string, any>;

  @Column('json', { nullable: true })
  output_data: Record<string, any>;

  @Column('text', { nullable: true })
  error_message: string;

  @CreateDateColumn()
  started_at: Date;

  @Column('timestamp', { nullable: true })
  ended_at: Date;

  @CreateDateColumn()
  created_at: Date;
} 