import re
from flask import jsonify, request, Response
from packaging_cycle import CycleJournal


def register(app, edge, path):
    journal = CycleJournal(path)

    @app.before_request
    def protect_cycle():
        pack = edge.packaging
        if not pack:
            return
        match = re.match(r'^/api/products/(\d+)(?:/|$)', request.path)
        if match and int(match[1]) == edge.cfg.product_id and pack.cycle_id and request.method in ('POST','PUT','DELETE'):
            return jsonify(error='包裝循環進行中，請先取走產品或中止此箱，再修改設定'), 409
        if request.path in ('/api/edge/sop/reset','/api/edge/sop/finish') and request.method == 'POST':
            return jsonify(error='影像包裝會自動完成與換箱；需要放棄此箱時請使用「中止此箱」'), 409

    @app.route('/api/edge/packaging/cancel', methods=['POST'])
    def cancel():
        with edge.control_lock:
            if not edge.packaging:
                return jsonify(error='尚未啟用影像包裝循環'), 409
            edge.packaging.cancel()
            summary = edge.packaging.summary()
            with edge.lock:
                edge.sop = summary
            return jsonify(success=edge.packaging.state != 'FAULT')

    @app.route('/api/edge/packaging/ack', methods=['POST'])
    def acknowledge():
        with edge.control_lock:
            if not edge.packaging or not edge.status()['inference_ready']:
                return jsonify(error='影像包裝循環尚未就緒'), 409
            edge.packaging.acknowledge()
            summary = edge.packaging.summary()
            with edge.lock:
                edge.sop = summary
            return jsonify(success=True)

    @app.route('/api/edge/packaging/history')
    def packaging_history():
        offset=max(0, request.args.get('offset',0,type=int))
        with journal.connect() as db:
            rows=db.execute('SELECT id,product_id,created,updated,status FROM cycles ORDER BY created DESC LIMIT 31 OFFSET ?', (offset,)).fetchall()
        return jsonify(items=[dict(x) for x in rows[:30]],more=len(rows)>30)

    @app.route('/api/edge/packaging/history/<cycle_id>')
    def detail(cycle_id):
        with journal.connect() as db:
            row=db.execute('SELECT * FROM cycles WHERE id=?',(cycle_id,)).fetchone()
            events=db.execute('SELECT id,created,kind,metadata,length(raw) AS has_image FROM events WHERE cycle_id=? ORDER BY created,rowid',(cycle_id,)).fetchall()
        if not row:
            return jsonify(error='找不到包裝紀錄'),404
        return jsonify(cycle=dict(row),events=[dict(x) for x in events])

    @app.route('/api/edge/packaging/evidence/<event_id>/<kind>')
    def packaging_evidence(event_id,kind):
        if kind not in ('raw','result','metadata'):
            return jsonify(error='找不到證據'),404
        with journal.connect() as db:
            row=db.execute(f'SELECT {kind} FROM events WHERE id=?',(event_id,)).fetchone()
        if not row or not row[0]:
            return jsonify(error='本事件沒有影像'),404
        return Response(row[0],mimetype='application/json' if kind=='metadata' else 'image/jpeg')

    return journal
