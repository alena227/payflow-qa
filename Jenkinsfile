// Jenkins Pipeline для PayFlow. Альтернатива GitHub Actions — тот же смысл, другой синтаксис.
// Запускается в Jenkins (профиль ci в docker-compose). Стадии идут по очереди.
pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    stages {
        stage('Поднять стенд') {
            steps {
                sh '''
                    cp .env.example .env
                    docker compose up -d --build
                    for i in $(seq 1 60); do
                        if curl -sf http://localhost:8000/health >/dev/null; then echo "api готов"; break; fi
                        sleep 3
                    done
                    docker compose exec -T api python -m app.seed
                '''
            }
        }

        stage('Python-тесты') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r tests/requirements.txt
                    python -m playwright install --with-deps chromium
                    pytest -v
                '''
            }
        }

        stage('Java-тесты') {
            steps {
                dir('java-tests') {
                    sh 'mvn -B test'
                }
            }
        }
    }

    post {
        always {
            // публикуем Allure-отчёт (нужен Allure Jenkins Plugin)
            allure includeProperties: false, results: [[path: 'allure-results'], [path: 'java-tests/target/allure-results']]
            sh 'docker compose down -v || true'
        }
        failure {
            echo 'Сборка упала — смотри логи выше и Allure-отчёт.'
        }
    }
}
