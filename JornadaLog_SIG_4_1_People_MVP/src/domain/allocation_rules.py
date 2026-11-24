from datetime import datetime

def validate_allocation(person, certification, availability, last_journey_end, allocation_start, min_rest_hours=11):
    checks=[]
    def add(rule, ok, reason=''):
        checks.append({'regra':rule,'status':'APROVADO' if ok else 'REPROVADO','bloqueante':not ok,'motivo':reason})
    add('CADASTRO', bool(person and person.get('active')), 'Pessoa inativa ou inexistente')
    add('DISPONIBILIDADE', bool(availability), 'Profissional indisponivel no periodo')
    add('CERTIFICACAO', bool(certification and certification.get('valid')), 'Certificacao ausente, vencida ou incompativel')
    if last_journey_end:
        rest=(allocation_start-last_journey_end).total_seconds()/3600
        add('DESCANSO', rest >= min_rest_hours, f'Descanso calculado: {rest:.1f}h; minimo: {min_rest_hours}h')
    else: add('DESCANSO', True)
    return {'resultado':'BLOQUEADO' if any(not c['status']=='APROVADO' for c in checks) else 'APTO','validacoes':checks}
