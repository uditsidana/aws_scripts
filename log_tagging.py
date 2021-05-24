#This function will tag Cloud Watch log groups same as lambdas
#Assumption is all my log groups are in one region in our ase it's eu-west-1 
#even if lambda's are in other region. Regions like gov or iso are not handled
import boto3
import botocore
import re
import logging
from botocore.config import Config
config = Config(
   retries = {
      'max_attempts': 10,
      'mode': 'standard'
   }
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
client = boto3.client('logs',config=config)
client_lambda = boto3.client('lambda')

#function to get log groups data in /aws/lambda/ accross regions
def get_log_groups():
    list = []
    response = client.describe_log_groups(logGroupNamePrefix='/aws/lambda/')
    list.append(response['logGroups'])
    try:
        new_token=response['nextToken']
        while new_token:
            response = client.describe_log_groups(logGroupNamePrefix='/aws/lambda',nextToken=new_token)
            list.append(response['logGroups'])
            try:
                new_token=response['nextToken']
            except:
                new_token=False
    except:
        pass

    return list
#function to get lambda names
def lambda_names():
    log_groups = []
    for instance in get_log_groups():
        for min_instance in instance:
            log_group_name = min_instance['logGroupName']
            non_omit = min_instance['arn']
            log_name_1 = non_omit.replace("arn:aws:logs", "arn:aws:lambda")
            log_name_2 = log_name_1.replace("log-group:/aws/lambda/","function:")
            lambda_name = log_name_2[:-2]
            log_groups.append(lambda_name)
    
    return log_groups

def tagging():
    count_tagged = 0
    count_not_tagged = 0
    count_delete = 0
    for lambda_arn in lambda_names():
        name_lambda = re.sub("arn:aws:lambda:\S+:\d+:\w+:","",lambda_arn)
        name_log_group = '/aws/lambda/' + name_lambda
        try:
            response_lambda = client_lambda.list_tags(Resource=lambda_arn)
            all_tags = response_lambda['Tags']
            response = client.tag_log_group(logGroupName=name_log_group,tags={'Project': all_tags.get('Project')})
            print("Resource tagged with Tag Project",name_log_group)
            count_tagged = count_tagged + 1
        except botocore.exceptions.ParamValidationError as error:
            print("Resource is not tagged with Project Tag",lambda_arn)
            count_not_tagged = count_not_tagged + 1
        except client_lambda.exceptions.ResourceNotFoundException as error:
            print("No resource found with ARN,it might be deleted or check the ARN: ",lambda_arn)
            count_delete = count_delete + 1
        except botocore.exceptions.ClientError as error:
            print("Checking the region, ", name_lambda)
            region_lambda = re.findall(r"[a-z]{2}-[a-z]+-\d{1}",name_lambda)
            region_lambda = str(region_lambda)
            region_lambda = region_lambda.replace("['","")
            region_lambda = region_lambda.replace("']","")
            
            client_lambda_region = boto3.client('lambda', region_name = region_lambda)
            name_region_lambda = re.sub("[a-z]{2}-[a-z]+-\d{1}.","",name_lambda)
        
            try:
                
                response_describe = client_lambda_region.get_function(FunctionName=name_region_lambda)
                lambda_new_arn = response_describe['Configuration']['FunctionArn']
                response_lambda_region = client_lambda_region.list_tags(Resource=lambda_new_arn)
                alltags = response_lambda_region['Tags']
                response_log_group = client.tag_log_group(logGroupName=name_log_group,tags={'Project': alltags.get('Project')})
                print("Resource tagged with Tag Project",name_log_group)
                count_tagged = count_tagged + 1
            except client_lambda.exceptions.ResourceNotFoundException as error:
                print("No lambda resource found with ARN,it might be deleted or check the ARN: ",lambda_new_arn)
                count_delete = count_delete + 1
            except botocore.exceptions.ParamValidationError as error:
                print("Lambda Resource is not tagged with Project Tag",lambda_new_arn)
                count_not_tagged = count_not_tagged + 1
    print("Resources tagged with Project Tag", count_tagged)
    print("Resources not tagged with Project Tag", count_not_tagged)
    print("Resources not found", count_delete)

    

def lambda_handler(event, context):
    tagging()

if __name__ == "__main__":
    lambda_handler(None, None)