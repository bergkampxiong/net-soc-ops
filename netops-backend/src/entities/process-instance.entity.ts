import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn, DeleteDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { ProcessDefinition } from './process-definition.entity';

@Entity('process_instances')
export class ProcessInstance {
  @PrimaryColumn('varchar', { length: 36 })
  id: string;

  @Column('varchar', { length: 36 })
  definition_id: string;

  @ManyToOne(() => ProcessDefinition)
  @JoinColumn({ name: 'definition_id' })
  definition: ProcessDefinition;

  @Column('varchar', { length: 100 })
  name: string;

  @Column('text', { nullable: true })
  description: string;

  @Column('varchar', { length: 20, default: 'running' })
  status: 'running' | 'completed' | 'terminated' | 'suspended' | 'failed';

  @Column('json', { nullable: true })
  variables: Record<string, any>;

  @Column('varchar', { length: 36, nullable: true })
  current_node: string;

  @Column('varchar', { length: 36 })
  started_by: string;

  @CreateDateColumn()
  started_at: Date;

  @Column('timestamp', { nullable: true })
  ended_at: Date;

  @Column('varchar', { length: 36 })
  created_by: string;

  @CreateDateColumn()
  created_at: Date;

  @Column('varchar', { length: 36 })
  updated_by: string;

  @UpdateDateColumn()
  updated_at: Date;

  @DeleteDateColumn()
  deleted_at: Date;
} 