INSERT OR IGNORE INTO users(id,name,email,role) VALUES
(1,'Usuário Demonstrativo','gestor@siglog.local','GESTOR_OPERACOES');
INSERT OR IGNORE INTO employees(id,name,registration,profile,unit,active) VALUES
(1,'Ana Souza','MOT-001','MOTORISTA','Matriz',1),
(2,'Carlos Lima','OPE-002','OPERADOR','Turno B',1),
(3,'Marina Alves','MOT-003','MOTORISTA','Matriz',1);
INSERT OR IGNORE INTO certifications(id,employee_id,type,code,expires_at,status) VALUES
(1,1,'Direção defensiva','DD-001','2027-05-20','VALIDA'),
(2,2,'Operação logística','OL-002','2026-12-01','PROXIMA_VENCIMENTO');
INSERT OR IGNORE INTO availabilities(id,employee_id,start_at,end_at,kind) VALUES
(1,1,'2026-11-18T00:00:00','2026-12-31T23:59:59','DISPONIVEL'),
(2,2,'2026-11-18T00:00:00','2026-12-31T23:59:59','DISPONIVEL');
INSERT OR IGNORE INTO shifts(id,code,name,unit,start_time,end_time,required_count,required_certification,status) VALUES
(1,'TA','Turno A','Matriz','06:00','14:00',2,'Direção defensiva','ATIVO'),
(2,'TB','Turno B','Matriz','14:00','22:00',3,NULL,'ATIVO');
INSERT OR IGNORE INTO schedules(id,shift_id,schedule_date,status) VALUES(1,1,'2026-11-19','CONFIRMADA'),(2,2,'2026-11-19','EM_VALIDACAO');
INSERT OR IGNORE INTO conflicts(id,employee_id,type,severity,description,status) VALUES
(1,2,'CERTIFICACAO','ALTA','Certificação próxima do vencimento','ABERTO'),
(2,NULL,'ESCALA_SEM_COBERTURA','CRITICA','Turno B possui duas posições abertas','ABERTO');
