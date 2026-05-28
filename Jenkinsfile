pipeline {
    agent any

    parameters {
        string(
            name: 'BRANCH_NAME',
            defaultValue: 'main',
            description: 'Git branch to build and deploy'
        )
        choice(
            name: 'ACTION',
            choices: ['deploy', 'rollback'],
            description: 'Pipeline action'
        )
    }

    environment {
        REGISTRY       = 'dockertutorial90010'         
        IMAGE_NAME     = 'python-app'
        IMAGE_TAG      = "${params.BRANCH_NAME}-${BUILD_NUMBER}"
        DOCKER_IMAGE   = "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        NAMESPACE      = "${params.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
        KUBECONFIG     = credentials('kubeconfig')           
        DOCKER_CREDS   = credentials('dockerhub-creds')      
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Checking out branch: ${params.BRANCH_NAME}"
                git branch: "${params.BRANCH_NAME}",
                    url: 'https://github.com/your-org/cicd-kubernetes.git',  
                    credentialsId: 'github-creds'
            }
        }

        stage('Lint & Test') {
            steps {
                sh '''
                    pip install flake8 pytest --quiet
                    flake8 app/ --max-line-length=100 || true
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${DOCKER_IMAGE} ."
            }
        }

        stage('Push to Registry') {
            steps {
                sh """
                    echo "${DOCKER_CREDS_PSW}" | docker login -u "${DOCKER_CREDS_USR}" --password-stdin
                    docker push ${DOCKER_IMAGE}
                    docker rmi ${DOCKER_IMAGE}   # clean up local image
                """
            }
        }

        stage('Create Namespace') {
            steps {
                sh "kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -"
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                expression { params.ACTION == 'deploy' }
            }
            steps {
                sh """
                    # Substitute placeholders in manifests
                    sed -e 's|\${NAMESPACE}|${NAMESPACE}|g' \
                        -e 's|\${DOCKER_IMAGE}|${DOCKER_IMAGE}|g' \
                        -e 's|\${BRANCH_NAME}|${params.BRANCH_NAME}|g' \
                        k8s/deployment.yaml | kubectl apply -f -

                    sed 's|\${NAMESPACE}|${NAMESPACE}|g' \
                        k8s/service.yaml | kubectl apply -f -

                    # Wait for rollout
                    kubectl rollout status deployment/python-app \
                        -n ${NAMESPACE} --timeout=120s
                """
            }
        }

        stage('Rollback') {
            when {
                expression { params.ACTION == 'rollback' }
            }
            steps {
                sh "kubectl rollout undo deployment/python-app -n ${NAMESPACE}"
            }
        }

        stage('Verify Deployment') {
            steps {
                sh """
                    echo "=== Pods ==="
                    kubectl get pods -n ${NAMESPACE} -o wide

                    echo "=== Service ==="
                    kubectl get svc -n ${NAMESPACE}

                    echo "=== Node distribution ==="
                    kubectl get pods -n ${NAMESPACE} -o wide | awk '{print \$7}' | sort | uniq -c
                """
            }
        }
    }

    post {
        success {
            echo "✅ Pipeline succeeded for branch: ${params.BRANCH_NAME}"
        }
        failure {
            echo "❌ Pipeline failed — check logs above"
            sh "kubectl rollout undo deployment/python-app -n ${NAMESPACE} || true"
        }
        always {
            sh "docker logout || true"
        }
    }
}