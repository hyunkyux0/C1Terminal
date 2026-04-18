# Shutting Down the C1 Terminal Match Runner

## Quick teardown (recommended)

```bash
cd replay-viewer
./teardown.sh
```

This deletes everything: EC2 instance, S3 bucket, security group, key pair, IAM role.

## Manual teardown

If the script doesn't work, delete these in the AWS Console (us-east-2):

1. **EC2 instance** — name: `c1terminal-runner` → Terminate
2. **S3 bucket** — name: `c1terminal-<account-id>` → Empty → Delete
3. **Security group** — name: `c1terminal-sg` → Delete (after instance is terminated)
4. **Key pair** — name: `c1terminal-key` → Delete
5. **IAM role** — name: `C1TerminalEC2Role` → Delete policies first → Delete role

Also delete the local key file:
```bash
rm replay-viewer/c1terminal-key.pem
rm replay-viewer/.deploy-info
```

## Cost check

If you forget to tear down, the t3.medium costs ~$1/day. Check for running instances:
```bash
aws ec2 describe-instances --filters "Name=tag:Name,Values=c1terminal-runner" "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[].InstanceId' --region us-east-2
```
