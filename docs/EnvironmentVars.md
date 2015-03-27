## SBAC_DEVOPS 

  Path to your srl-devops checkout.  Subdirs should be tools, ansible, credentials, etc.

## SBAC_ENV

  Which environment and security tier we are in.  This is used to select credentials from pass(1).

  For details on what the heck a security tier is, see https://docs.google.com/a/amplify.com/document/d/1P_gdQucDoMKZNSSMNFsMNbwJBxSyoCzSIS4K23V5azo/edit

  Format: ENVNAME/TIERNAME
  Example: 
    dev/inventory

  Valid values for ENVNAME:
   - dev
   - prod
   - stage
   - qa

  Valid values for TIERNAME:
   - inventory
   - security
   - spinup

