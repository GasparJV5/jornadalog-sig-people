import os
from src.api.app_factory import create_app
app = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('APP_PORT','5000')), debug=os.getenv('APP_ENV')=='development')
