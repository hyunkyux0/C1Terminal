#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_INFO="$PROJECT_DIR/replay-viewer/.deploy-info"

if [ ! -f "$DEPLOY_INFO" ]; then
    echo "No deployment found. (.deploy-info missing)"
    echo "If you deployed manually, delete these resources:"
    echo "  - EC2 instance tagged 'c1terminal-runner'"
    echo "  - Security group 'c1terminal-sg'"
    echo "  - Key pair 'c1terminal-key'"
    echo "  - S3 bucket 'c1terminal-<account-id>'"
    echo "  - IAM role 'C1TerminalEC2Role'"
    exit 1
fi

source "$DEPLOY_INFO"

echo "=== C1 Terminal Match Runner — Teardown ==="
echo ""
echo "This will DELETE all of the following:"
echo "  - EC2 instance: $INSTANCE_ID"
echo "  - S3 bucket:    $BUCKET_NAME (all contents)"
echo "  - Security group: $SG_ID"
echo "  - Key pair:     $KEY_NAME"
echo "  - IAM role:     C1TerminalEC2Role"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# 1. Terminate EC2 instance
echo "[1/5] Terminating EC2 instance $INSTANCE_ID..."
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$REGION" > /dev/null 2>&1 || true
echo "  Waiting for termination..."
aws ec2 wait instance-terminated --instance-ids "$INSTANCE_ID" --region "$REGION" 2>/dev/null || true
echo "  Done."

# 2. Empty and delete S3 bucket
echo "[2/5] Deleting S3 bucket $BUCKET_NAME..."
aws s3 rm "s3://$BUCKET_NAME" --recursive --region "$REGION" 2>/dev/null || true
aws s3 rb "s3://$BUCKET_NAME" --region "$REGION" 2>/dev/null || true
echo "  Done."

# 3. Delete security group
echo "[3/5] Deleting security group $SG_ID..."
aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION" 2>/dev/null || true
echo "  Done."

# 4. Delete key pair
echo "[4/5] Deleting key pair $KEY_NAME..."
aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION" 2>/dev/null || true
rm -f "$PROJECT_DIR/replay-viewer/$KEY_NAME.pem"
echo "  Done."

# 5. Delete IAM role
echo "[5/5] Deleting IAM role..."
aws iam delete-role-policy --role-name C1TerminalEC2Role --policy-name S3Access 2>/dev/null || true
aws iam remove-role-from-instance-profile --instance-profile-name C1TerminalEC2Role --role-name C1TerminalEC2Role 2>/dev/null || true
aws iam delete-instance-profile --instance-profile-name C1TerminalEC2Role 2>/dev/null || true
aws iam delete-role --role-name C1TerminalEC2Role 2>/dev/null || true
echo "  Done."

# Cleanup local files
rm -f "$DEPLOY_INFO"

echo ""
echo "=========================================="
echo "  ALL RESOURCES DELETED"
echo "=========================================="
echo ""
echo "  Verify in AWS Console if needed:"
echo "  https://console.aws.amazon.com/ec2/home?region=$REGION"
echo "=========================================="
