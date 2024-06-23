packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = "~> 1"
    }
  }
}

variable "demo_account_id" {
  type        = string
  description = "this is the demo accout id "
}

variable "source_ami" {
  type        = string
  description = "The source AMI ID to use as a base"
}

variable "ami_name" {
  type        = string
  description = "The name of the custom AMI"
}

variable "aws_region" {
  type        = string
  description = "The aws region ID to use"
}

variable "aws_access_key" {
  type        = string
  description = "AWS access key"
}

variable "aws_secret_access_key" {
  type        = string
  description = "AWS secret key"
}



source "amazon-ebs" "custom" {
  ami_name      = var.ami_name
  source_ami    = var.source_ami
  instance_type = "t2.micro"
  ssh_username  = "admin"
  region        = var.aws_region

  access_key = var.aws_access_key
  secret_key = var.aws_secret_access_key


  ami_users = [var.demo_account_id] # Add the AWS account IDs that can use the AMI

}


build {
  sources = ["source.amazon-ebs.custom"]

  provisioner "shell" {
    inline = [
      "echo 'Customization steps here'",
      "sudo apt-get update",
      "echo 'Additional customization steps here'",
      "sudo apt install -y zip"
    ]
  }

  provisioner "file" {
    source      = "my-repo-files.zip"
    destination = "~/my-repo-files.zip"
  }


  provisioner "shell" {
    inline = [
      "sudo groupadd csye6225",
      "sudo useradd -s /bin/false -g csye6225 -d /opt/csye6225 -m csye6225",
      "sudo mv my-repo-files.zip /opt/csye6225/",
      "echo 'unzipping the file'",
      "cd /opt/csye6225/",
      "sudo unzip /opt/csye6225/my-repo-files.zip -d . ",
      "echo 'changing the permissions of script file and running the script'",
      "sudo chmod +x ./debian_script.sh",
      "sudo chown -R csye6225:csye6225 /opt/csye6225",
      "sudo ./debian_script.sh",
      "sudo apt remove git -y",
      "ls -al",
      "sudo mv my_fastapi_app.service /etc/systemd/system/",
      "sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb",
      "sudo dpkg -i -E ./amazon-cloudwatch-agent.deb",
      "sudo systemctl daemon-reload",
      "sudo systemctl enable my_fastapi_app",
      "sudo systemctl start my_fastapi_app",
    ]
  }


}
