
# !/bin/bash
set -e

# Print environment variables
echo "Environment Variables:"
echo "MINIO_SERVER_HOST: ${MINIO_SERVER_HOST}"
echo "MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}"
echo "MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}"
echo "GEMINI_STORAGE_ACCESS_KEY: ${GEMINI_STORAGE_ACCESS_KEY}"
echo "GEMINI_STORAGE_SECRET_KEY: ${GEMINI_STORAGE_SECRET_KEY}"
echo "GEMINI_STORAGE_BUCKET_NAME: ${GEMINI_STORAGE_BUCKET_NAME}"

# Get environment variables
echo "Connect to MinIO server..."
mc alias set local http://${MINIO_SERVER_HOST}:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

# Create a service account
echo "Creating service account..."
mc admin user add local "${GEMINI_STORAGE_ACCESS_KEY}" "${GEMINI_STORAGE_SECRET_KEY}"

# Create a policy file
echo "Creating policy file..."
POLICY_FILE="/tmp/policy.json"
cat << EOF > "${POLICY_FILE}"
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "s3:CreateBucket",
            "s3:DeleteBucket",
            "s3:GetObject",
            "s3:DeleteObject",
            "s3:PutObject",
            "s3:ListBucket",
            "s3:List*",
            "s3:GetBucketLocation",
            "s3:AbortMultipartUpload",
            "s3:ListBucketMultipartUploads",
            "s3:ListMultipartUploadParts"
        ],
        "Resource": [
            "arn:aws:s3:::${GEMINI_STORAGE_BUCKET_NAME}",
            "arn:aws:s3:::${GEMINI_STORAGE_BUCKET_NAME}/*",
            "arn:aws:s3:::staged-downloads/*",
            "arn:aws:s3:::staged-uploads/*"    
        ]
    }]
}
EOF

# Add policy with verbose output
echo "Adding policy..."
mc admin policy create local gemini-service-policy "${POLICY_FILE}" --debug

# Show policy
echo "Showing policy info..."
mc admin policy info local gemini-service-policy

# Clean up temporary policy file
rm -f "${POLICY_FILE}"

# Assign policy to service account
echo "Assigning policy to service account..."
mc admin policy attach local gemini-service-policy --user "${GEMINI_STORAGE_ACCESS_KEY}"

# Create bucket if it doesn't exist
echo "Creating bucket..."
mc mb local/"${GEMINI_STORAGE_BUCKET_NAME}"

# Create 'staged-downloads' bucket if it doesn't exist
if ! mc ls local/"staged-downloads" >/dev/null 2>&1; then
    echo "Creating 'staged-downloads' bucket..."
    mc mb local/"staged-downloads"
else
    echo "'staged-downloads' bucket already exists."
fi

# Create 'staged-uploads' bucket if it doesn't exist
if ! mc ls local/"staged-uploads" >/dev/null 2>&1; then
    echo "Creating 'staged-uploads' bucket..."
    mc mb local/"staged-uploads"
else
    echo "'staged-uploads' bucket already exists."
fi



# Set bucket to private
# echo "Setting bucket to private..."
# mc policy set download local/"${GEMINI_STORAGE_BUCKET_NAME}"
# mc policy set download local/"staged-downloads"
# mc policy set download local/"staged-uploads"

mc anonymous set download local/"${GEMINI_STORAGE_BUCKET_NAME}"
mc anonymous set download local/"staged-downloads"
mc anonymous set download local/"staged-uploads"


echo "MinIO initialization completed successfully"
