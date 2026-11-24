from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
from src.infrastructure.database import connect, init_db
from src.domain.allocation_rules import validate_allocation

def rows(cur): return [dict(x) for x in cur.fetchall()]
def create_app():
    app=Flask(__name__, static_folder='../../static', static_url_path='')
    CORS(app); init_db()
    @app.get('/')
    def home(): return send_from_directory(app.static_folder,'index.html')
    @app.get('/health')
    def health(): return {'status':'UP','service':'siglog-people','database':'sqlite'}
    @app.get('/api/session')
    def session(): return {'user':{'name':'Usuário Demonstrativo','initials':'UD','role':request.args.get('role','GESTOR_OPERACOES')}}
    @app.get('/api/dashboard')
    def dashboard():
        with connect() as c:
            q=lambda sql: c.execute(sql).fetchone()[0]
            return jsonify({'profissionaisAtivos':q('select count(*) from employees where active=1'),'disponiveisAgora':q("select count(distinct employee_id) from availabilities where kind='DISPONIVEL'"),'jornadasAtivas':q("select count(*) from journeys where status in ('INICIADA','EM_INTERVALO')"),'escalasDoDia':q('select count(*) from schedules'),'conflitosPendentes':q("select count(*) from conflicts where status='ABERTO'"),'certificacoesAVencer':q("select count(*) from certifications where status in ('PROXIMA_VENCIMENTO','VENCIDA')")})
    @app.route('/api/employees',methods=['GET','POST'])
    def employees():
        with connect() as c:
            if request.method=='GET': return jsonify(rows(c.execute('select * from employees order by name')))
            d=request.get_json() or {}
            if any(not d.get(k) for k in ('name','registration','profile')): return {'erro':'Nome, matrícula e perfil são obrigatórios.'},400
            try:
                cur=c.execute('insert into employees(name,registration,profile,unit,active) values(?,?,?,?,1)',(d['name'],d['registration'],d['profile'],d.get('unit','Matriz'))); return {'id':cur.lastrowid,'mensagem':'Profissional cadastrado.'},201
            except Exception: return {'erro':'Matrícula já cadastrada.'},409
    @app.get('/api/certifications')
    def certifications_get():
        with connect() as c: return jsonify(rows(c.execute('select c.*,e.name employee_name from certifications c join employees e on e.id=c.employee_id order by c.expires_at')))
    @app.post('/api/certifications')
    def certifications_post():
        d=request.get_json() or {}
        with connect() as c:
            cur=c.execute('insert into certifications(employee_id,type,code,issuer,issued_at,expires_at,status) values(?,?,?,?,?,?,?)',(d['employeeId'],d['type'],d.get('code'),d.get('issuer'),d.get('issuedAt'),d.get('expiresAt'),d.get('status','VALIDA'))); return {'id':cur.lastrowid},201
    @app.get('/api/availabilities')
    def availabilities_get():
        with connect() as c: return jsonify(rows(c.execute('select a.*,e.name employee_name from availabilities a join employees e on e.id=a.employee_id order by a.start_at desc')))
    @app.post('/api/availabilities')
    def availabilities_post():
        d=request.get_json() or {}
        with connect() as c:
            cur=c.execute('insert into availabilities(employee_id,start_at,end_at,kind) values(?,?,?,?)',(d['employeeId'],d['startAt'],d['endAt'],d.get('kind','DISPONIVEL'))); return {'id':cur.lastrowid},201
    @app.get('/api/shifts')
    def shifts_get():
        with connect() as c: return jsonify(rows(c.execute('select * from shifts order by code')))
    @app.post('/api/shifts')
    def shifts_post():
        d=request.get_json() or {}
        with connect() as c:
            cur=c.execute('insert into shifts(code,name,unit,start_time,end_time,required_count,required_certification) values(?,?,?,?,?,?,?)',(d['code'],d['name'],d.get('unit','Matriz'),d['startTime'],d['endTime'],d.get('requiredCount',1),d.get('requiredCertification'))); return {'id':cur.lastrowid},201
    @app.route('/api/schedules',methods=['GET','POST'])
    def schedules():
        with connect() as c:
            if request.method=='GET': return jsonify(rows(c.execute('select s.*,sh.name shift_name,sh.start_time,sh.end_time,sh.required_count from schedules s join shifts sh on sh.id=s.shift_id order by s.schedule_date desc')))
            d=request.get_json() or {}; cur=c.execute('insert into schedules(shift_id,schedule_date,status) values(?,?,?)',(d['shiftId'],d['date'],d.get('status','RASCUNHO'))); return {'id':cur.lastrowid},201
    @app.post('/api/allocations/validate')
    def allocation_validate():
        d=request.get_json() or {}; eid=d.get('employeeId'); start=datetime.fromisoformat(d['startAt'])
        with connect() as c:
            p=c.execute('select * from employees where id=?',(eid,)).fetchone(); cert=c.execute("select * from certifications where employee_id=? and status='VALIDA'",(eid,)).fetchone(); av=c.execute("select * from availabilities where employee_id=? and kind='DISPONIVEL' and start_at<=? and end_at>=?",(eid,d['startAt'],d['startAt'])).fetchone(); j=c.execute('select end_at from journeys where employee_id=? and end_at is not null order by end_at desc limit 1',(eid,)).fetchone()
        r=validate_allocation({'active':bool(p['active'])} if p else None,{'valid':True} if cert else None,av,datetime.fromisoformat(j['end_at']) if j else None,start,int(os.getenv('REST_MIN_HOURS','11'))); r['pessoa']=p['name'] if p else 'Não encontrada'; return jsonify(r)
    @app.post('/api/allocations')
    def allocate():
        d=request.get_json() or {}
        with connect() as c:
            cur=c.execute('insert into allocations(schedule_id,employee_id,status) values(?,?,?)',(d['scheduleId'],d['employeeId'],'CONFIRMADA')); c.execute('insert into domain_events(event_type,status,payload) values(?,?,?)',('MotoristaEscalado','PENDENTE',str(d))); return {'id':cur.lastrowid,'event':'MotoristaEscalado','eventStatus':'PENDENTE'},201
    @app.get('/api/conflicts')
    def conflicts():
        with connect() as c: return jsonify(rows(c.execute('select c.*,e.name employee_name from conflicts c left join employees e on e.id=c.employee_id order by c.created_at desc')))
    @app.put('/api/conflicts/<int:item_id>/resolve')
    def resolve_conflict(item_id):
        with connect() as c: c.execute("update conflicts set status='RESOLVIDO' where id=?",(item_id,)); return {'mensagem':'Conflito resolvido.'}
    @app.get('/api/notifications')
    def notifications():
        with connect() as c: return jsonify(rows(c.execute("select id,type,severity,description,status from conflicts where status='ABERTO' order by id desc limit 6")))
    return app
