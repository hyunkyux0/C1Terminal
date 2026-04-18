#!/bin/bash
set -e

# ── Config ────────────────────────────────────────────────────
REGION="us-east-2"
INSTANCE_TYPE="t3.medium"
KEY_NAME="c1terminal-key"
SG_NAME="c1terminal-sg"
AMI_ID=""  # Will be auto-detected
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="c1terminal-${ACCOUNT_ID}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== C1 Terminal Match Runner — Deploy ==="
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Bucket: $BUCKET_NAME"
echo ""

# ── 1. Create S3 bucket ──────────────────────────────────────
echo "[1/6] Creating S3 bucket..."
if aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
    echo "  Bucket already exists."
else
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"
    echo "  Created."
fi

# ── 2. Create key pair ───────────────────────────────────────
echo "[2/6] Creating key pair..."
KEY_FILE="$PROJECT_DIR/replay-viewer/$KEY_NAME.pem"
if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$REGION" 2>/dev/null; then
    echo "  Key pair already exists."
else
    aws ec2 create-key-pair \
        --key-name "$KEY_NAME" \
        --query 'KeyMaterial' \
        --output text \
        --region "$REGION" > "$KEY_FILE"
    chmod 400 "$KEY_FILE"
    echo "  Created: $KEY_FILE"
fi

# ── 3. Create security group ─────────────────────────────────
echo "[3/6] Creating security group..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region "$REGION")

SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || echo "None")

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "C1 Terminal Match Runner" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' --output text \
        --region "$REGION")
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0 --region "$REGION"
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 --region "$REGION"
    echo "  Created: $SG_ID"
else
    echo "  Already exists: $SG_ID"
fi

# ── 4. Find latest Amazon Linux 2023 AMI ─────────────────────
echo "[4/6] Finding AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text --region "$REGION")
echo "  AMI: $AMI_ID"

# ── 5. Launch EC2 instance ────────────────────────────────────
echo "[5/6] Launching EC2 instance..."

# Create user-data script
USER_DATA=$(cat <<'USERDATA'
#!/bin/bash
set -ex

# Install dependencies
dnf install -y python3-pip java-17-amazon-corretto unzip

# Create app directory
mkdir -p /opt/c1terminal
cd /opt/c1terminal

# Install Python dependencies
pip3 install fastapi uvicorn boto3 python-multipart

# The deploy script will SCP files here, then start the server
echo "Setup complete, waiting for app files..." > /opt/c1terminal/setup_done
USERDATA
)

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --user-data "$USER_DATA" \
    --iam-instance-profile Name=C1TerminalEC2Role 2>/dev/null \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=c1terminal-runner}]" \
    --query 'Instances[0].InstanceId' --output text \
    --region "$REGION" 2>/dev/null || true)

# If IAM role doesn't exist, try without it and create inline policy
if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" = "None" ]; then
    echo "  Creating IAM role for S3 access..."

    # Create the role
    aws iam create-role \
        --role-name C1TerminalEC2Role \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' 2>/dev/null || true

    # Attach S3 policy
    aws iam put-role-policy \
        --role-name C1TerminalEC2Role \
        --policy-name S3Access \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [{
                \"Effect\": \"Allow\",
                \"Action\": [\"s3:*\"],
                \"Resource\": [\"arn:aws:s3:::$BUCKET_NAME\", \"arn:aws:s3:::$BUCKET_NAME/*\"]
            }]
        }" 2>/dev/null || true

    # Create instance profile
    aws iam create-instance-profile \
        --instance-profile-name C1TerminalEC2Role 2>/dev/null || true
    aws iam add-role-to-instance-profile \
        --instance-profile-name C1TerminalEC2Role \
        --role-name C1TerminalEC2Role 2>/dev/null || true

    echo "  Waiting for IAM profile propagation..."
    sleep 10

    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_NAME" \
        --security-group-ids "$SG_ID" \
        --user-data "$USER_DATA" \
        --iam-instance-profile Name=C1TerminalEC2Role \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=c1terminal-runner}]" \
        --query 'Instances[0].InstanceId' --output text \
        --region "$REGION")
fi

echo "  Instance: $INSTANCE_ID"

# Wait for instance to be running
echo "  Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text --region "$REGION")
echo "  Public IP: $PUBLIC_IP"

# ── 6. Upload app files ──────────────────────────────────────
echo "[6/6] Uploading application files..."
echo "  Waiting for SSH to be ready..."
for i in $(seq 1 30); do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$KEY_FILE" ec2-user@"$PUBLIC_IP" "echo ok" 2>/dev/null; then
        break
    fi
    sleep 5
done

# Wait for user-data to finish
echo "  Waiting for instance setup..."
for i in $(seq 1 30); do
    if ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" ec2-user@"$PUBLIC_IP" "test -f /opt/c1terminal/setup_done" 2>/dev/null; then
        break
    fi
    sleep 5
done

# Fix ownership so ec2-user can write
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" ec2-user@"$PUBLIC_IP" \
    "sudo chown -R ec2-user:ec2-user /opt/c1terminal"

# Upload files
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" \
    "$PROJECT_DIR/replay-viewer/app.py" \
    "$PROJECT_DIR/replay-viewer/index.html" \
    "$PROJECT_DIR/engine.jar" \
    "$PROJECT_DIR/game-configs.json" \
    ec2-user@"$PUBLIC_IP":/opt/c1terminal/

# Start the server
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" ec2-user@"$PUBLIC_IP" bash <<REMOTE
cd /opt/c1terminal
export S3_BUCKET="$BUCKET_NAME"
export ENGINE_JAR="/opt/c1terminal/engine.jar"
export GAME_CONFIGS="/opt/c1terminal/game-configs.json"
nohup sudo -E python3 -m uvicorn app:app --host 0.0.0.0 --port 80 > /opt/c1terminal/server.log 2>&1 &
echo "Server started"
REMOTE

echo ""
echo "=========================================="
echo "  DEPLOYED SUCCESSFULLY!"
echo "=========================================="
echo ""
echo "  URL:  http://$PUBLIC_IP"
echo ""
echo "  Instance: $INSTANCE_ID"
echo "  Region:   $REGION"
echo "  Bucket:   $BUCKET_NAME"
echo ""
echo "  SSH:  ssh -i $KEY_FILE ec2-user@$PUBLIC_IP"
echo ""
echo "  To shut down: ./teardown.sh"
echo "=========================================="

# Save deployment info for teardown
cat > "$PROJECT_DIR/replay-viewer/.deploy-info" <<EOF
INSTANCE_ID=$INSTANCE_ID
REGION=$REGION
BUCKET_NAME=$BUCKET_NAME
KEY_NAME=$KEY_NAME
SG_NAME=$SG_NAME
SG_ID=$SG_ID
PUBLIC_IP=$PUBLIC_IP
EOF
