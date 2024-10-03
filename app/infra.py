import launchflow as lf

if lf.environment == "gcp-dev":
    # Secrets
    openai_api_key = lf.gcp.SecretManagerSecret("openai-api-key")
    claude_api_key = lf.gcp.SecretManagerSecret("claude-api-key")
    # Redis
    redis_vm = lf.gcp.ComputeEngineRedis("rate-limit-redis")
    # Cloud Run (main deployment)
    app = lf.gcp.CloudRunService(
        name="htmlflow-app",
        dockerfile="Dockerfile",
        build_ignore=["lambda_handler.py", "aws-requirements.txt"],
        domain="htmlflow.dev",
    )


elif lf.environment == "aws-dev":
    # Secrets
    openai_api_key = lf.aws.SecretsManagerSecret("openai-api-key")
    claude_api_key = lf.aws.SecretsManagerSecret("claude-api-key")
    # Redis
    redis_vm = lf.aws.EC2Redis("rate-limit-redis")
    # AWS Lambda (main deployment)
    app = lf.aws.LambdaService(
        name="htmlflow-app",
        handler="main.handler",
        runtime=lf.aws.lambda_service.PythonRuntime(
            requirements_txt_path="requirements.txt"
        ),
        use_vpc=False,  # For public access without a NAT gateway $$$
        build_ignore=["Dockerfile", "gcp-requirements.txt"],
        # domain="htmlflow.dev",  TODO
    )


else:
    raise ValueError(f"Environment {lf.environment} is not set up")
