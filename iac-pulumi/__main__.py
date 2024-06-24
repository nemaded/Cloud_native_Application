import pulumi
import pulumi_aws 
import boto3
from pulumi_aws import ec2, Provider, get_availability_zones, Provider
from pulumi_aws import rds
# from pulumi_aws_native import rds

import ipaddress


print("hi")

aws_profile=pulumi.Config("aws").require("profile")
aws_vpccidr = pulumi.Config("vpc").require("cidrBlock")
aws_region=pulumi.Config("aws").require("region")
key_pair_name=pulumi.Config("vpc").require("ssh_key_pair")
port_no=pulumi.Config("vpc").require("port_no")
host_name=pulumi.Config("host_name").require("name")

# Create a new VPC
vpc = ec2.Vpc("vpc",
            cidr_block=aws_vpccidr,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            tags={
              "Name": "New_VPC",
            },

              
              
)

# Create a new Internet Gateway and a 
# 
# ttach it to the VPC
gateway = ec2.InternetGateway("gateway",
                            vpc_id=vpc.id,
                            tags={
                              "Name": "main-gateway",
                            },

)
az_list = pulumi.Config("vpc").require("availabilityZones").split(',')
print(f"inputazs{az_list}")
available_azs = get_availability_zones(state="available").names
print (f"available_azs{available_azs}")

invalid_azs = [az for az in az_list if az not in available_azs]

try:
    if invalid_azs:
        raise ValueError(f"Invalid availability zone(s): {', '.join(invalid_azs)}")


    desired_az_count = min(3, len(az_list))
    print(desired_az_count)
    
    # Calculate subnet CIDR blocks dynamically based on desired AZs
    vpc_cidr = ipaddress.ip_network(aws_vpccidr)
    subnet_cidr_blocks = list(vpc_cidr.subnets(new_prefix=24))[:desired_az_count+5]

    
        # Create a public subnet in each availability zone
    public_subnets = [ec2.Subnet(f"public-subnet-{i+1}",
        vpc_id=vpc.id,
        cidr_block=str(subnet_cidr_blocks[i]),
        map_public_ip_on_launch=True,
        availability_zone=az,
        tags={
            "Name": f"public-subnet-{i+1}",
        }
    ) for i, az in enumerate(az_list)]

    # Create a private subnet in each availability zone
    private_subnets = [ec2.Subnet(f"private-subnet-{i+1}",
        vpc_id=vpc.id,
        cidr_block=str(subnet_cidr_blocks[i+4]),
        map_public_ip_on_launch=False,
        availability_zone=az,
        tags={
            "Name": f"private-subnet-{i+1}",
        }
    ) for i, az in enumerate(az_list)]

    private_subnet_ids = [subnet.id for subnet in private_subnets]

    # Create an RDS subnet group
    rds_subnet_group = pulumi_aws.rds.SubnetGroup("my-rds-subnet-group",
        subnet_ids=private_subnet_ids,
        description="Subnet group for RDS instances",
    )
    
    # Create a public Route Table
    public_route_table = ec2.RouteTable("public-route-table",
        vpc_id=vpc.id,
        tags={
            "Name": "Public Route Table",
        }
    )

    # Create a private Route Table
    private_route_table = ec2.RouteTable("private-route-table",
        vpc_id=vpc.id,
        tags={
            "Name": "Private Route Table",
        }
    )

    # Associate public subnets with the public route table
    for i, subnet in enumerate(public_subnets):
        ec2.RouteTableAssociation(f"public-subnet-association-{i}",
            subnet_id=subnet.id,
            route_table_id=public_route_table.id,
        )

    # Associate private subnets with the private route table
    for i, subnet in enumerate(private_subnets):
        ec2.RouteTableAssociation(f"private-subnet-association-{i}",
            subnet_id=subnet.id,
            route_table_id=private_route_table.id,
        )

    # Create a Route in the public route table to direct traffic to the Internet Gateway
    ec2.Route("public-route",
        route_table_id=public_route_table.id,
        destination_cidr_block="0.0.0.0/0",
        gateway_id=gateway.id,  # Connect to the Internet Gateway
    )

    
    # Create the application security group
    app_security_group = ec2.SecurityGroup("app-security-group",
        vpc_id=vpc.id,
        tags={
            "Name": "Application Security Group",
        }
    )

    app_security_group_rule_ssh = ec2.SecurityGroupRule("app-security-group-rule-ssh",
    type="ingress",
    from_port=22,
    to_port=22,
    protocol="tcp",
    cidr_blocks=["0.0.0.0/0"],  # Allow from anywhere
    security_group_id=app_security_group.id,
    ) 
    app_security_group_rule_http = ec2.SecurityGroupRule("app-security-group-rule-http",
    type="ingress",
    from_port=80,
    to_port=80,
    protocol="tcp",
    cidr_blocks=["0.0.0.0/0"],  # Allow from anywhere
    security_group_id=app_security_group.id,
    )

    app_security_group_rule_https = ec2.SecurityGroupRule("app-security-group-rule-https",
        type="ingress",
        from_port=443,
        to_port=443,
        protocol="tcp",
        cidr_blocks=["0.0.0.0/0"],  # Allow from anywhere
        security_group_id=app_security_group.id,
    )
    

    # Replace 'APP_PORT' with your application's specific port
    app_port = port_no
    app_security_group_rule_app = ec2.SecurityGroupRule("app-security-group-rule-app",
        type="ingress",
        from_port=app_port,
        to_port=app_port,
        protocol="tcp",
        cidr_blocks=["0.0.0.0/0"],  # Allow from anywhere
        security_group_id=app_security_group.id,
    )    
        # Your custom AMI name
    # custom_ami_name = "debian12-custom-ami"  # Replace with your AMI name

    # Create an AWS EC2 client using boto3
    ec2_client = boto3.session.Session(profile_name=aws_profile).client("ec2")
    # Use boto3 to search for the custom AMI
    response = ec2_client.describe_images(ExecutableUsers=['self'], Filters=[{'Name': 'image-type', 'Values': ['machine']}])
    sorted_images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)

    custom_ami_id=0
    if sorted_images:
        custom_ami_id = sorted_images[0]['ImageId']
        print(f"Latest AMI ID (based on creation time): {custom_ami_id}")
    else:
        print("No AMIs found.")

    if custom_ami_id:
        # The custom AMI was found
        custom_ami_id = custom_ami_id

        outbound_rule = ec2.SecurityGroupRule("outbound-rule",
            type="egress",
            from_port=8000,
            to_port=8000,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=app_security_group.id,
        )
        
    else:
        print("Custom AMI not found.")

    # print("this is the RDS instance")
    # Create the RDS security group
    rds_security_group = pulumi_aws.ec2.SecurityGroup("database-security-group",
        vpc_id=vpc.id,  # Replace with your VPC ID
        name="database-security-group",
        description="Security group for RDS instances",
    )

    # Add a rule to allow PostgreSQL traffic from the application security group
    # Assuming you have an `app_security_group` defined elsewhere
    pulumi_aws.ec2.SecurityGroupRule("rds-ingress-rule",
        type="ingress",
        from_port=5432,
        to_port=5432,
        protocol="tcp",
        security_group_id=rds_security_group.id,
        source_security_group_id=app_security_group.id,  # Replace with your application security group ID
    )

    
    # Creating a custom Parameter group for Postgres 15
    custom_pg = pulumi_aws.rds.ParameterGroup("csye6255",  # Set the name to "CSYE6225THRU"
        family="postgres15",
        )
    rds_instance = pulumi_aws.rds.Instance("my-instance",
        allocated_storage=20,  # You can adjust the allocated storage as needed
        storage_type="gp2",
        engine="postgres",
        engine_version=15,
        instance_class="db.t3.micro",
        parameter_group_name=custom_pg.name,  # Using the custom parameter group
        db_name="csye6225",
        username="csye6225",
        password="Darshan16",  # Replace with a strong password
        skip_final_snapshot=True,  # Prevents creating a final snapshot
        multi_az=False,  # Disable Multi-AZ deployment
        publicly_accessible=False,  # Disable public accessibility
        db_subnet_group_name=rds_subnet_group.name,
        vpc_security_group_ids=[rds_security_group.id],
        )
    rds_endpoint = rds_instance.endpoint
    db_name = rds_instance.db_name
    db_username = rds_instance.username
    db_password = rds_instance.password 

    service_content = ["[Unit]",
    "Description=My FastAPI Application",
    "After=network.target",
    "",
    "[Service]",
    "User=root",
    "WorkingDirectory=/home/admin",
    "ExecStart=/home/admin/myenv/bin/python3 /home/admin/myenv/bin/uvicorn App.main:app",
    "Restart=always",
    "",
    "[Install]",
    "WantedBy=multi-user.target"
    ]
    service_content_str = '\n'.join(service_content)
   
    user_data = pulumi.Output.all(rds_endpoint, db_name, db_username, db_password).apply(
    lambda args : f"""#!/bin/bash
    echo  RDS_ENDPOINT={args[0]} > /opt/csye6225/.env
    echo "DATABASE_NAME={args[1]}" >> /opt/csye6225/.env
    echo "USER={args[2]}" >> /opt/csye6225/.env
    echo "PGPASSWORD={args[3]}" >> /opt/csye6225/.env
    sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/csye6225/amazon-cloudwatch-agent.json -s
    """
    )

    # Create IAM role for the EC2 instance
    ec2_role = pulumi_aws.iam.Role('ec2Role',
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                }
            }]
        }"""
    )
        # Attach the AWS-managed CloudWatchAgentServer policy to the role
    policy_attachment = pulumi_aws.iam.RolePolicyAttachment('CloudWatchAgentServerPolicyAttachment',
        role=ec2_role.name,
        policy_arn='arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy')

    # Create an Instance Profile for the role
    instance_profile = pulumi_aws.iam.InstanceProfile('ec2InstanceProfile', role=ec2_role.name)


    ec2_instance = ec2.Instance("ec2-instance",
                ami=custom_ami_id,
                instance_type="t2.micro",
                subnet_id=public_subnets[0].id,
                security_groups=[app_security_group.id],
                key_name=key_pair_name,  # Attach the key pair
                iam_instance_profile=instance_profile.name,

                associate_public_ip_address=True,
                tags={
                    "Name": "MyEC2Instance",
                },
                root_block_device=ec2.InstanceRootBlockDeviceArgs(
                    volume_size=25,
                    volume_type='gp2',
                    delete_on_termination=True,
                ),
                disable_api_termination=False,
                user_data=user_data
            )
    ec2.SecurityGroupRule("ec2-to-rds-outbound-rule",
    type="egress",
    from_port=5432,             # Source port
    to_port=5432,               # Destination port
    protocol="tcp",
    source_security_group_id=rds_security_group.id,  # Reference to the RDS security group
    security_group_id=app_security_group.id  # Your EC2 instance's security group ID
    )
    ec2.SecurityGroupRule("ec2-to-internet-https-outbound-rule",
    type="egress",
    from_port=443,               # Source port for HTTPS
    to_port=443,                 # Destination port for HTTPS
    protocol="tcp",
    cidr_blocks=["0.0.0.0/0"],   # Allow to all IP addresses
    security_group_id=app_security_group.id  # Your EC2 instance's security group ID
    )

    
    public_ip = ec2_instance.public_ip

    hosted_zone = pulumi_aws.route53.get_zone(name=host_name)


    record = pulumi_aws.route53.Record("app-dns-record",
        zone_id=hosted_zone.id,
        name=host_name,
        type="A",
        ttl=300,
        records=[public_ip],
    )


    
   


except ValueError as e:
    # Handle the exception
    print(f"An error occurred: {e}")
pulumi.export('vpc_id', vpc.id)
pulumi.export('public_ip',public_ip)
pulumi.export('hosted_zone', hosted_zone)
