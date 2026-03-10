# Uncomment after creating the S3 bucket and DynamoDB table.
# Run these commands first to create the backend resources:
#
#   aws s3api create-bucket \
#     --bucket devops-project-tfstate \
#     --region ap-south-1 \
#     --create-bucket-configuration LocationConstraint=ap-south-1
#
#   aws s3api put-bucket-versioning \
#     --bucket devops-project-tfstate \
#     --versioning-configuration Status=Enabled
#
#   aws dynamodb create-table \
#     --table-name devops-project-tflock \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST \
#     --region ap-south-1

# terraform {
#   backend "s3" {
#     bucket         = "devops-project-tfstate"
#     key            = "production/terraform.tfstate"
#     region         = "ap-south-1"
#     dynamodb_table = "devops-project-tflock"
#     encrypt        = true
#   }
# }
