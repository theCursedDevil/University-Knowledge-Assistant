# Jenkins CI/CD Pipeline Demonstration Guide
## Generative AI-Based University Knowledge Assistant (UKA)

This guide provides end-to-end instructions for demonstrating automated continuous integration and continuous deployment (CI/CD) using **Jenkins**, **Docker**, and **Kubernetes**.

---

## 1. Architecture Overview

```
                      +---------------------------------------+
                      |               Git Push                |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |         Stage 1: Checkout             |
                      +-------------------+-------------------+
                                          |
                      +-------------------v-------------------+
                      |      Stage 2: Quality Gates           |
                      |   (Parallel Containerized Checks)     |
                      +---------+---------+---------+---------+
                                |         |         |
                   +------------+   +-----+---+   +-+-----------+
                   | Backend    |   | Backend |   | Frontend    |
                   | Lint (Ruff)|   | Pytest  |   | Lint/Build  |
                   +------------+   +---------+   +-------------+
                                          |
                      +-------------------v-------------------+
                      |        Stage 3: Docker Build          |
                      |          (Parallel Stages)            |
                      +---------+-------------------+---------+
                                |                   |
                   +------------+-----+       +-----+------------+
                   | Backend Image    |       | Frontend Image   |
                   | (Multi-Stage)    |       | (Next.js Runner) |
                   +------------------+       +------------------+
                                          |
                      +-------------------v-------------------+
                      |     Stage 4: Docker Registry Push     |
                      |    (Tagged with Commit SHA + latest)  |
                      +-------------------+-------------------+
                                          |
                      +-------------------v-------------------+
                      |    Stage 5: Deploy to Staging (K8s)   |
                      |         (Rolling Update)              |
                      +-------------------+-------------------+
                                          |
                      +-------------------v-------------------+
                      |       Stage 6: Smoke Tests            |
                      |    (API Health & Route Verification)  |
                      +-------------------+-------------------+
                                          |
                      +-------------------v-------------------+
                      |   Stage 7: Manual Approval Gate       |
                      |       (Production Deployment)         |
                      +---------------------------------------+
```

---

## 2. Fast Track: Jenkins Service Details

Your local Jenkins instance is already running and ready:

| Property | Value |
|---|---|
| **Jenkins Web UI** | [http://localhost:9090](http://localhost:9090) |
| **Container Name** | `uka-jenkins` |
| **Initial Admin Password** | `e5a92f3ce84e491cae6b7e8c9bd987b4` |
| **Docker Socket** | Mounted at `/var/run/docker.sock` (Docker-in-Docker enabled) |
| **Jenkinsfile Path** | `Jenkinsfile` in repository root |

---

## 3. Step-by-Step Demonstration Walkthrough

### Step 1: Log in to Jenkins
1. Open your browser and navigate to: [http://localhost:9090](http://localhost:9090)
2. Enter the Administrator password:
   ```text
   e5a92f3ce84e491cae6b7e8c9bd987b4
   ```
3. Click **"Install suggested plugins"** (takes ~1-2 minutes).
4. Create an admin user or click **"Skip and continue as admin"**.
5. Keep the Jenkins URL as `http://localhost:9090/` and click **"Save and Finish"**.

---

### Step 2: Create the Pipeline Job
1. On the Jenkins dashboard, click **"New Item"** (left sidebar).
2. Enter item name: `UKA-CI-CD-Pipeline`.
3. Select **"Pipeline"** and click **"OK"**.
4. In the configuration page, scroll down to the **Pipeline** section:
   - **Definition**: Select `Pipeline script from SCM` (or `Pipeline script` for direct copy).
   - If using `Pipeline script`: Copy and paste the entire contents of `Jenkinsfile`.
   - If using `Pipeline script from SCM`:
     - **SCM**: Git
     - **Repository URL**: Path to your repo or GitHub URL
     - **Script Path**: `Jenkinsfile`
5. Click **"Save"**.

---

### Step 3: Trigger a Build (Demonstrating Quality Gates & Image Build)
1. On the job page, click **"Build with Parameters"** (or **"Build Now"**).
2. You will see interactive parameters configured for this demo:
   - `RUN_QUALITY_GATES`: Checked (`true`)
   - `BUILD_DOCKER_IMAGES`: Checked (`true`)
   - `PUSH_DOCKER_IMAGES`: Unchecked (or checked if you configured GHCR credentials)
   - `DEPLOY_STAGING`: Unchecked (or checked if you configured K8s)
   - `DEPLOY_PRODUCTION`: Unchecked
3. Click **"Build"**.

---

### Step 4: What to Highlight During Your Demo

1. **Stage View & Parallelism**:
   - Show how **Stage 2 (Quality Gates)** runs Backend Linting, Backend Unit Tests, and Frontend Linting concurrently in parallel branches.
   - Show how **Stage 3 (Docker Build)** builds both `university-knowledge-assistant-backend` and `university-knowledge-assistant-frontend` simultaneously.

2. **Immutable Artifact Tagging**:
   - Point out that every build tags Docker images with the exact Git commit SHA (e.g. `university-knowledge-assistant-backend:<short-sha>`) plus `:latest`.

3. **Console Log Cleanliness**:
   - Click on the build number (e.g., `#1`) → **"Console Output"**.
   - Show the structured banner outputs:
     - `✓ Stage 1 completed successfully.`
     - `✓ Stage 2a PASSED: Backend linting clean.`
     - `✓ Stage 2b PASSED: Backend automated tests passed.`
     - `✓ Stage 3a PASSED: Backend image built.`
     - `✓ Stage 3b PASSED: Frontend image built.`

4. **Security & Manual Approval Gate**:
   - Explain how Production rollout (Stage 7) cannot occur automatically; it is locked behind an `input` step requiring administrative sign-off.

---

## 4. CLI Validation Commands

You can run automated verification directly from terminal:

```bash
# Run the Jenkinsfile test suite
./scripts/ci/test-jenkinsfile.sh

# View live Jenkins container logs
docker logs -f uka-jenkins

# Stop/Restart Jenkins anytime
docker-compose -f jenkins/docker-compose.jenkins.yml restart
```
