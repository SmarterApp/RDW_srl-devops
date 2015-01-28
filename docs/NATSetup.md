## NAT General Info 

  The NAT is needed for anything without a public IP, aka anything with an 10.0.0.0/8 IP only, to connect
  out to the global Internet. 

  There are 3 subnets associated with each VPC with the following properties: 
  - Public: Route out is through the igw on the VPC and anything with a public IP should be put here
  - Private: Route out is through the NAT server, nothing with a public IP should be put here
  - LZ: Route out is through the igw, public IPs can be put here. This is for the LZ servers only

## NAT Turn-Up process

  After the VPC has been turned up, there should be three subnets, tagged with the above labels.

  Turn up the NAT server using the ami labeled "nat," which has the ansible user with the dev pubkey 
  It should have at least the srl-nat security group, but the srl-default and omniti-fulton-office are needed
  if you want to SSH into it. 

  No post-configuration is needed on the server itself. 

  In the AWS console for EC2, under Instances, checkbox the NAT server and go to: 
  Actions -> Networking -> Change Source/Dest. Check
  Confirm that you want to disable this check
  
  Copy the Instance ID for the NAT server, we'll need it later

  On the AWS console for VPC, under Route Tables: 
  Create Route Table and wait for it to be created
  Find your new route table in the list, and click on it then: 
  Routes tab -> Edit
  Add a new route with the following properties below the "local" route

  Destination: 0.0.0.0/0
  Target: The NAT instance id from earlier

  Click Save

  Click on the Subnet Associations Tab -> Edit
  Checkbox the Private subnet for this VPC and click Save. 

  No modification is needed for LZ or Public subnets
