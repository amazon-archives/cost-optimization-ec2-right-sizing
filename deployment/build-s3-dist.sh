#!/bin/bash

# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#sudo yum-config-manager --enable epel
#sudo yum update -y
#sudo pip install --upgrade pip
#alias sudo='sudo env PATH=$PATH'
#sudo  pip install --upgrade setuptools
#sudo pip install --upgrade virtualenv

# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name
# source-bucket-base-name should be the base name for the S3 bucket location where the template will source the Lambda code from.
# The template will append '-[region_name]' to this bucket name.
# For example: ./build-s3-dist.sh solutions
# The template will then expect the source code to be located in the solutions-[region_name] bucket

# Check to see if input has been provided:
if [ -z "$1" ]; then
    echo "Please provide the base S3 object prefix where the scripts will eventually reside.\nFor example: ./build-s3-dist.sh solutions-reference"
    exit 1
fi

# Build source
echo "Staring to build distribution"
echo "export deployment_dir=`pwd`"
export deployment_dir=`pwd`
echo "mkdir -p dist"
mkdir -p dist
echo "cp -f cost-optimization-ec2-right-sizing.template dist"
cp -f cost-optimization-ec2-right-sizing.template dist
echo "Updating code source bucket in template with $1"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace dist/cost-optimization-ec2-right-sizing.template"
sed -i '' -e $replace dist/cost-optimization-ec2-right-sizing.template
echo "Updating code source version in template with $2"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace dist/cost-optimization-ec2-right-sizing.template"
sed -i '' -e $replace dist/cost-optimization-ec2-right-sizing.template
echo "cp $deployment_dir/../source/scripts/*.py dist"
cp $deployment_dir/../source/scripts/*.py dist
echo "Completed building distribution"
cd $deployment_dir
