pipeline {
  agent any

  options {
    skipDefaultCheckout(true)
  }

  environment {
    NAMESPACE = 'default'

    CASINO_APP_NAME = 'casino-site'
    PROVIDER_APP_NAME = 'game-provider'

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

    stage('Create Kubernetes Deployment YAML') {
      steps {
        writeFile file: 'deploymentservice.yml', text: """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${CASINO_APP_NAME}
  namespace: ${NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${CASINO_APP_NAME}
  template:
    metadata:
      labels:
        app: ${CASINO_APP_NAME}
    spec:
      containers:
        - name: ${CASINO_APP_NAME}
          image: ${IMAGE_REPO}:${IMAGE_TAG}
          imagePullPolicy: Always
          command: ["python"]
          args: ["app.py"]
          ports:
            - containerPort: 5000
          env:
            - name: SECRET_KEY
              value: "change-this-secret-key"
            - name: DATABASE
              value: "/data/casino.db"
            - name: GAME_PROVIDER_URL
              value: "https://provider.dev.local"
            - name: GAME_LAUNCH_SECRET
              value: "dev-game-launch-secret-change-this"
            - name: WALLET_API_SECRET
              value: "dev-wallet-secret-change-this"
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
  name: ${CASINO_APP_NAME}-service
  namespace: ${NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: ${CASINO_APP_NAME}
  ports:
    - name: http
      port: 80
      targetPort: 5000

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${PROVIDER_APP_NAME}
  namespace: ${NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${PROVIDER_APP_NAME}
  template:
    metadata:
      labels:
        app: ${PROVIDER_APP_NAME}
    spec:
      containers:
        - name: ${PROVIDER_APP_NAME}
          image: ${IMAGE_REPO}:${IMAGE_TAG}
          imagePullPolicy: Always
          command: ["python"]
          args: ["game-provider/app.py"]
          ports:
            - containerPort: 5100
          env:
            - name: PYTHONPATH
              value: "/app"
            - name: PROVIDER_SECRET_KEY
              value: "change-this-provider-secret"
            - name: GAME_LAUNCH_SECRET
              value: "dev-game-launch-secret-change-this"
            - name: WALLET_API_SECRET
              value: "dev-wallet-secret-change-this"
            - name: CASINO_WALLET_API_URL
              value: "http://casino-site-service/provider-api/wallet"

---
apiVersion: v1
kind: Service
metadata:
  name: ${PROVIDER_APP_NAME}-service
  namespace: ${NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: ${PROVIDER_APP_NAME}
  ports:
    - name: http
      port: 80
      targetPort: 5100
"""
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        script {
          kubernetesDeploy(
            configs: "deploymentservice.yml",
            kubeconfigId: "${KUBECONFIG_ID}"
          )
        }
      }
    }

    stage('Result') {
      steps {
        echo "SUCCESS: Casino app and game provider deployed to Kubernetes"
        echo "Image deployed: ${IMAGE_REPO}:${IMAGE_TAG}"
        echo "Casino service: casino-site-service"
        echo "Provider service: game-provider-service"
      }
    }
  }

  post {
    failure {
      echo "FAILED: Check the failed stage above."
    }

    success {
      echo "DONE: Docker image pushed and Kubernetes Deployments + Services applied."
    }
  }
}
