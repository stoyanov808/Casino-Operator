pipeline {
  agent any

  options {
    skipDefaultCheckout(true)
  }

  environment {
    APP_NAME = 'casino-site'
    NAMESPACE = 'default'

    IMAGE_REPO = 'stoyanov808/casino-site'
    IMAGE_TAG = "${env.BUILD_NUMBER}"

    DOCKER_CREDENTIALS_ID = 'DockerHub'
    KUBECONFIG_ID = 'kubernetes'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build Docker Image') {
      steps {
        sh """
          docker build \
            -t ${IMAGE_REPO}:${IMAGE_TAG} \
            -t ${IMAGE_REPO}:latest \
            .
        """
      }
    }

    stage('Push Docker Image') {
      steps {
        script {
          docker.withRegistry('https://index.docker.io/v1/', "${DOCKER_CREDENTIALS_ID}") {
            docker.image("${IMAGE_REPO}:${IMAGE_TAG}").push()
            docker.image("${IMAGE_REPO}:latest").push()
          }
        }
      }
    }

    stage('Create Kubernetes YAML') {
      steps {
        writeFile file: 'casino-k8s.yml', text: """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: casino-db-pvc
  namespace: ${NAMESPACE}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${APP_NAME}
  template:
    metadata:
      labels:
        app: ${APP_NAME}
    spec:
      containers:
        - name: ${APP_NAME}
          image: ${IMAGE_REPO}:${IMAGE_TAG}
          imagePullPolicy: Always
          ports:
            - containerPort: 5000
          env:
            - name: SECRET_KEY
              value: "change-this-secret-key"
            - name: DATABASE
              value: "/data/casino.db"
          volumeMounts:
            - name: casino-db-storage
              mountPath: /data
      volumes:
        - name: casino-db-storage
          persistentVolumeClaim:
            claimName: casino-db-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: ${APP_NAME}-service
  namespace: ${NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: ${APP_NAME}
  ports:
    - port: 80
      targetPort: 5000
"""
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        withKubeConfig([credentialsId: "${KUBECONFIG_ID}"]) {
          sh """
            kubectl apply -f casino-k8s.yml
            kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s
          """
        }
      }
    }

    stage('Verify Kubernetes') {
      steps {
        withKubeConfig([credentialsId: "${KUBECONFIG_ID}"]) {
          sh """
            kubectl get pvc -n ${NAMESPACE}
            kubectl get deployment ${APP_NAME} -n ${NAMESPACE}
            kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME}
            kubectl get service ${APP_NAME}-service -n ${NAMESPACE}
          """
        }
      }
    }

    stage('Result') {
      steps {
        echo "SUCCESS: Casino app deployed to Kubernetes"
        echo "Image deployed: ${IMAGE_REPO}:${IMAGE_TAG}"
      }
    }
  }

  post {
    failure {
      echo "FAILED: Check the failed stage above."
    }

    success {
      echo "DONE: Docker image pushed and Kubernetes deployment applied."
    }
  }
}
