pipeline {
    agent any

    // Branch name passed as a build parameter
    // Determines which branch to build and which namespace to deploy to
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
        GCP_PROJECT  = 'project-e7559e94-76d0-4195-9ad'           // ← replace with your GCP project ID
        GCP_REGION   = 'us-central1'               // ← replace with your cluster region
        CLUSTER_NAME = 'autopilot-cluster-1'         // ← replace with your GKE cluster name
        REGISTRY     = "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/python-app"
        IMAGE_NAME   = 'python-app'
        IMAGE_TAG    = "${params.BRANCH_NAME}-${BUILD_NUMBER}"
        DOCKER_IMAGE = "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

        // main branch deploys to production, all other branches deploy to staging
        NAMESPACE    = "${params.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
    }

    stages {

        
        stage('Checkout') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "${params.BRANCH_NAME}"]],
                    userRemoteConfigs: [[
                        url: 'https://github.com/ayushd49/cicd-kubernetes.git',
                        credentialsId: 'github-creds'
                    ]]
                ])
                echo "Checked out branch: ${params.BRANCH_NAME}"
            }
        }

        stage('Configure GCP Auth') {
            steps {
                sh """
                    # VM service account is attached — no key file needed
                    # gcloud reads credentials from GCP metadata server automatically
                    gcloud config set project ${GCP_PROJECT}
                    gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev --quiet

                    # Fetch GKE cluster credentials into kubeconfig
                    gcloud container clusters get-credentials ${CLUSTER_NAME} \
                        --region ${GCP_REGION} \
                        --project ${GCP_PROJECT}

                    echo "GCP auth configured successfully"
                    gcloud auth list
                """
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    echo "Building image: ${DOCKER_IMAGE}"
                    docker build -t ${DOCKER_IMAGE} .
                """
            }
        }

        stage('Push to Artifact Registry') {
            steps {
                sh """
                    echo "Pushing image: ${DOCKER_IMAGE}"
                    docker push ${DOCKER_IMAGE}

                    # Clean up local image to free disk space on VM
                    docker rmi ${DOCKER_IMAGE}
                    echo "Push successful"
                """
            }
        }

        stage('Create Namespace') {
            steps {
                sh """
                    # dry-run + apply is idempotent — safe to run even if namespace exists
                    kubectl create namespace ${NAMESPACE} \
                        --dry-run=client -o yaml | kubectl apply -f -
                """
            }
        }

        stage('Deploy to GKE') {
            when {
                expression { params.ACTION == 'deploy' }
            }
            steps {
                sh """
                    echo "Deploying to namespace: ${NAMESPACE}"

                    # Replace placeholders in deployment.yaml with actual values
                    sed -e 's|NAMESPACE_PLACEHOLDER|${NAMESPACE}|g' \
                        -e 's|IMAGE_PLACEHOLDER|${DOCKER_IMAGE}|g' \
                        -e 's|BRANCH_PLACEHOLDER|${params.BRANCH_NAME}|g' \
                        k8s/deployment.yaml | kubectl apply -f -

                    # Replace namespace placeholder in service.yaml
                    sed 's|NAMESPACE_PLACEHOLDER|${NAMESPACE}|g' \
                        k8s/service.yaml | kubectl apply -f -

                    # Wait for deployment to complete
                    # Timeout is 300s because GKE Autopilot provisions nodes on demand
                    kubectl rollout status deployment/python-app \
                        -n ${NAMESPACE} --timeout=300s
                """
            }
        }

        stage('Rollback') {
            when {
                expression { params.ACTION == 'rollback' }
            }
            steps {
                sh """
                    echo "Rolling back deployment in namespace: ${NAMESPACE}"
                    kubectl rollout undo deployment/python-app -n ${NAMESPACE}
                    kubectl rollout status deployment/python-app \
                        -n ${NAMESPACE} --timeout=300s
                """
            }
        }

        stage('Verify Deployment') {
            steps {
                sh """
                    echo "=== Pods ==="
                    kubectl get pods -n ${NAMESPACE} -o wide

                    echo "=== Service (may take 1-2 mins for EXTERNAL-IP) ==="
                    kubectl get svc -n ${NAMESPACE}

                    echo "=== Waiting for pods to be ready ==="
                    kubectl wait --for=condition=ready pod \
                        -l app=python-app \
                        -n ${NAMESPACE} \
                        --timeout=300s
                """
            }
        }

    }

    post {
        success {
            echo "✅ Pipeline succeeded — Branch: ${params.BRANCH_NAME} | Namespace: ${NAMESPACE}"
            sh "kubectl get svc python-app-service -n ${NAMESPACE}"
        }
        failure {
            echo "❌ Pipeline failed — attempting rollback"
            sh "kubectl rollout undo deployment/python-app -n ${NAMESPACE} || true"
        }
        always {
            sh "docker logout || true"
        }
    }
}