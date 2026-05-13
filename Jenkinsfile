pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Validar Conexión Git') {
            steps {
                echo "✅ Jenkins logró leer el Jenkinsfile sin errores de sintaxis."
            }
        }

        stage('Validar Entorno del Servidor (Windows)') {
            steps {
                echo "Verificando qué herramientas tiene instaladas Jenkins por dentro..."
                // Usamos 'bat' en lugar de 'sh' para sistemas Windows
                bat "git --version"
                bat "python --version"
                bat "docker --version"
            }
        }

        stage('Instalar Dependencias') {
            steps {
                echo "📦 Instalando dependencias Python..."
                bat """
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                """
            }
        }

        stage('Validar Código (Lint)') {
            steps {
                echo "🔍 Ejecutando validación de código con Flake8..."
                // Se agregó la nueva app 'medico' al escaneo
                bat """
                    flake8 src/admision src/core src/triage src/medico --max-line-length=120 --statistics
                """
            }
        }

        stage('Formateo de Código (Black)') {
            steps {
                echo "🎨 Verificando formateo de código con Black..."
                // Ahora revisa todo el directorio src/ para garantizar que tu limpieza global se mantenga
                bat """
                    black --check --line-length=120 src/
                """
            }
        }

        stage('Ejecutar Tests Unitarios + Cobertura') {
            steps {
                echo "🧪 Ejecutando suite de tests con pytest + cobertura..."
                // Se excluye 'e2e' aquí para que no falle por falta de RabbitMQ, y se añade 'medico' a la cobertura
                bat """
                    cd src
                    pytest -k "not e2e" --cov=admision --cov=core --cov=triage --cov=medico --cov-report=html --cov-report=term-missing --cov-fail-under=80 -v
                    cd ..
                """
            }
        }

        stage('Performance Testing (< 1.5s)') {
            steps {
                echo "⚡ Validando performance de vistas (< 1.5s)..."
                bat """
                    cd src
                    pytest admision/tests.py::PacienteCreateViewTests::test_response_time_menor_1_5_segundos -v
                    cd ..
                """
            }
        }

        stage('Pruebas de Integración') {
            steps {
                echo "🔗 Ejecutando pruebas de integración..."
                bat """
                    cd src
                    pytest admision/tests.py::PacienteListViewTests -v
                    pytest admision/tests.py::PacienteCreateViewTests -v
                    pytest admision/tests.py::PacienteUpdateViewTests -v
                    pytest admision/tests.py::PacienteDeleteViewTests -v
                    pytest triage/tests.py::TriajeModelAndViewTests -v
                    cd ..
                """
            }
        }

        stage('Pruebas E2E (EDA con RabbitMQ)') {
            // Jenkins inyecta esta variable de entorno solo durante esta etapa
            environment {
                CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672//"
            }
            steps {
                echo "🐇 Levantando RabbitMQ temporal en Docker..."
                bat "docker run -d --rm --name rabbitmq-temp -p 5672:5672 rabbitmq:3-management"

                echo "🔗 Ejecutando prueba de flujo asíncrono (Triaje -> Celery -> ColaEstado)..."
                bat """
                    cd src
                    pytest tests/e2e/test_triaje_queue.py::test_triaje_flow_with_real_rabbitmq -v
                    cd ..
                """
            }
        }
    }

    post {
        always {
            echo "🧹 Apagando infraestructura de pruebas..."
            // Usamos || echo ... para que Jenkins no falle si el contenedor ya había sido destruido
            bat "docker stop rabbitmq-temp || echo 'El contenedor rabbitmq-temp ya estaba detenido'"

            echo "📊 Generando reporte HTML de cobertura..."
            publishHTML([
                reportDir: 'src/htmlcov',
                reportFiles: 'index.html',
                reportName: '📈 Coverage Report',
                keepAll: true,
                alwaysLinkToLastBuild: true
            ])
        }

        success {
            echo "✅ BUILD EXITOSO"
            echo "  ✓ Cobertura ≥ 80%"
            echo "  ✓ Todos los tests unitarios y E2E pasaron"
            echo "  ✓ Flujo asíncrono validado"
        }

        failure {
            echo "❌ BUILD FALLIDO"
            echo "  Verifica los logs arriba para más detalles"
            echo "  Posibles causas:"
            echo "    - Tests fallaron"
            echo "    - Cobertura < 80%"
            echo "    - RabbitMQ no pudo iniciar"
            echo "    - Errores de linting/formateo"
        }

        unstable {
            echo "⚠️ BUILD INESTABLE - Revisa los warnings"
        }
    }
}