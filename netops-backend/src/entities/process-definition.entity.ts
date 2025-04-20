import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn, DeleteDateColumn } from 'typeorm';

@Entity('process_definitions')
export class ProcessDefinition {
  @PrimaryColumn('varchar', { length: 36 })
  id: string;

  @Column('varchar', { length: 100 })
  name: string;

  @Column('text', { nullable: true })
  description: string;

  @Column('int', { default: 1 })
  version: number;

  @Column('varchar', { length: 20, default: 'draft' })
  status: 'draft' | 'published' | 'disabled';

  @Column('json')
  nodes: any[];

  @Column('json')
  edges: any[];

  @Column('json', { nullable: true })
  variables: Record<string, any>;

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