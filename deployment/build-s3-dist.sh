#!/bin/bash  
#  
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned  
#  
# This script should be run from the repo's deployment directory  
# cd deployment  
# ./build-s3-dist.sh source-bucket-base-name trademarked-solution-name version-code  
#  
# Paramenters:  
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda  
#    code from. The template will append '-[region_name]' to this bucket name.  
#    For example: ./build-s3-dist.sh solutions my-solution v1.0.0  
#    The template will then expect the source code to be located in the solutions-[region_name] bucket  
#  
#  - trademarked-solution-name: name of the solution for consistency  
#  
#  - version-code: version of the package  
  
# Check to see if input has been provided:  
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then  
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."  
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"  
    exit 1  
fi  

do_cmd () {
	echo "------ EXEC $*"
	$*
}

# On entry it is expected that we are in the deployment folder of the build
 
# Get reference for all important folders  
template_dir="$PWD"  
template_dist_dir="$template_dir/global-s3-assets"  
build_dist_dir="$template_dir/regional-s3-assets"  
source_dir="../source"  

echo "------------------------------------------------------------------------------"  
echo "[Init] Clean old dist folders"  
echo "------------------------------------------------------------------------------"  
do_cmd rm -rf $template_dist_dir  
do_cmd mkdir -p $template_dist_dir  
do_cmd rm -rf $build_dist_dir  
do_cmd mkdir -p $build_dist_dir  
 
echo "------------------------------------------------------------------------------"  
echo "[Packing] Templates"  
echo "------------------------------------------------------------------------------"  
do_cmd cp -R $template_dir/*.template $template_dist_dir/ 
 
echo "Updating code source bucket in template with $1"  
replace="s/%%BUCKET_NAME%%/$1/g" 
do_cmd sed -i -e $replace $template_dist_dir/*.template 
 
replace="s/%%SOLUTION_NAME%%/$2/g" 
do_cmd sed -i -e $replace $template_dist_dir/*.template 
 
replace="s/%%VERSION%%/$3/g" 
do_cmd sed -i -e $replace $template_dist_dir/*.template 
 
replace="s/%%TEMPLATE_BUCKET_NAME%%/$4/g" 
do_cmd sed -i -e $replace $template_dist_dir/*.template 
 
echo "------------------------------------------------------------------------------"  
echo "[Packing] Scripts"  
echo "------------------------------------------------------------------------------"  
do_cmd cp $template_dir/../source/scripts/*.py $build_dist_dir

echo "------------------------------------------------------------------------------"  
echo "[Packing] Solution Helper"  
echo "------------------------------------------------------------------------------"  
echo "------ Building local-solution-helper ZIP file"
cd $build_dist_dir
do_cmd virtualenv env
do_cmd source env/bin/activate
do_cmd pip install $template_dir/../source/local-solution-helper/. --target=$template_dir/dist/env/lib/python3.7/site-packages/ --upgrade --upgrade-strategy only-if-needed
# do_cmd pip install requests --target=$template_dir/dist/env/lib/python3.7/site-packages/ --upgrade --upgrade-strategy only-if-needed

# fail build if pip install fails
instl_status=$?
if [ ${instl_status} != '0' ]; then
  echo "------ FAILED pip install solution helper status: ${instl_status}"
  exit ${instl_status}
fi
echo "------ Solution Helper package built ------"
cd $template_dir/dist/env/lib/python3.7/site-packages/

do_cmd zip -r9 $build_dist_dir/local-solution-helper.zip .

echo "Clean up build material in $VIRTUAL_ENV"
do_cmd rm -rf $VIRTUAL_ENV

echo "------------------------------------------------------------------------------"  
echo "Completed building distribution"
echo "------------------------------------------------------------------------------"  
