// =============================================================================
// Jenkins Job DSL — Seed Job
// Auto-creates the UKA CI/CD pipeline job via Job DSL plugin.
// Configure this as a "Freestyle project" → "Process Job DSLs" build step
// pointing to: jenkins/jobs/seed-job.groovy
// =============================================================================

pipelineJob('UKA-CI-CD-Pipeline') {
    displayName('University Knowledge Assistant — CI/CD Pipeline')
    description('''
        <h3>Generative AI-Based University Knowledge Assistant</h3>
        <p>Full CI/CD pipeline: Lint → Test → Docker Build → Push → Deploy</p>
        <ul>
            <li><strong>Backend:</strong> FastAPI + PostgreSQL + Qdrant + Redis</li>
            <li><strong>Frontend:</strong> Next.js 15 (Standalone)</li>
            <li><strong>IAM:</strong> Keycloak (OAuth 2.0 / OIDC)</li>
            <li><strong>Infra:</strong> Docker → Kubernetes</li>
        </ul>
    '''.stripIndent())

    // Keep last 20 builds
    logRotator {
        numToKeep(20)
    }

    // SCM trigger (every 2 minutes) — replace with webhook for production
    triggers {
        scm('H/2 * * * *')
    }

    // Pipeline definition from SCM
    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url('https://github.com/your-org/university-knowledge-assistant.git')
                        credentials('github-credentials')
                    }
                    branches('*/main', '*/develop')
                }
            }
            scriptPath('Jenkinsfile')
            lightweight(true)
        }
    }

    // Pipeline properties
    properties {
        disableConcurrentBuilds()
    }
}

// Multibranch pipeline variant (auto-discovers branches and PRs)
multibranchPipelineJob('UKA-Multibranch') {
    displayName('UKA — Multibranch Pipeline')
    description('Automatically builds all branches and pull requests.')

    branchSources {
        github {
            id('uka-github-source')
            repoOwner('your-org')
            repository('university-knowledge-assistant')
            credentialsId('github-credentials')
        }
    }

    orphanedItemStrategy {
        discardOldItems {
            numToKeep(10)
        }
    }

    factory {
        workflowBranchProjectFactory {
            scriptPath('Jenkinsfile')
        }
    }
}
