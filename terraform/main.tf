provider "aws" {
  region = "ap-south-1"
}

resource "aws_security_group" "devops_sg" {
  name = "devops-security-group"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "devops_server" {
  ami           = "ami-03f4878755434977f"
  instance_type = "t2.micro"
  key_name      = "revanth"

  vpc_security_group_ids = [aws_security_group.devops_sg.id]

  tags = {
    Name = "devops-project-server"
  }
}