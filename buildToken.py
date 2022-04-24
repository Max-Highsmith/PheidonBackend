import pdb
import os
import subprocess
from pathlib import Path

#Network Parameters
CARDANO_NETWORK_MAGIC = 1097911063
CARDANO_CLI_PATH = "cardano-cli"
PROTOCOL_PARAMS = "protocol.json"

#Pheidon Parameters
GARBAGE_GOOBER="addr_test1qzjn8jm4w3pdr8ut6r8082nke88lj77ydvyukmvrd7mxyj9ev5h025wjlsx7mj8hmx3zna8ycgjwq6sycuyp0yche3dqkjahhu"
PHEIDON_CHEST="addr_test1vzj9r2xufz2dplq9j0tzfu8lxsszgq2dfm5ualdgwkgpr7sramg2d"
BUILDER_ADDRESS="addr_test1vzj9r2xufz2dplq9j0tzfu8lxsszgq2dfm5ualdgwkgpr7sramg2d"
POSEIDON="addr_test1qrvum5l26caapku3hkpul20n6kytkpdrldy86h4k99rxwt9le0epmdexwccmh53lrwr5fw2fzzywmfnt5tkqulfdnzzqsdsf5v"

out = subprocess.check_output(['ls'])

def computeFee(raw_mat):
    feestr = subprocess.check_output([
        CARDANO_CLI_PATH,
        "transaction",
        "calculate-min-fee",
        "--tx-body-file",
        raw_mat,
        "--tx-in-count",
        str(1),
        "--tx-out-count",
        str(2),
        "--testnet-magic",
        str(CARDANO_NETWORK_MAGIC),
        "--witness-count",
        str(2),
        "--protocol-params-file",
        PROTOCOL_PARAMS]
        )
    return int(feestr.decode('utf-8').split("\n")[0].split()[0])


def queryUTXOTop(walletAddress):
    rawUtxoTable = subprocess.check_output([
        CARDANO_CLI_PATH,
        'query', 'utxo',
        '--testnet-magic', str(CARDANO_NETWORK_MAGIC),
        '--address', walletAddress
        ])
    utxoTableRows = rawUtxoTable.strip().splitlines()
    firstRow = utxoTableRows[2].decode("utf-8")
    txhash, txix, funds = firstRow.split()[0:3]
    print(txhash, txix, funds)
    return txhash, txix, funds


def buildPolicy(tokenName):
    policy_path = "policies/policy_"+tokenName
    policy_vkey = policy_path+"/policy.vkey"
    policy_skey = policy_path+"/policy.skey"
    policy_script = policy_path+"/policy.script"
    policy_id = policy_path+"/policyID"
    Path(policy_path).mkdir(parents=True,
            exist_ok=True)
    buildPolicyKeys = subprocess.check_output([
        CARDANO_CLI_PATH,
        "address", "key-gen",
        "--verification-key-file", policy_vkey,
        "--signing-key-file", policy_skey 
        ])
    
    policyKeyHash = subprocess.check_output([
        CARDANO_CLI_PATH,
        "address", "key-hash",
        "--payment-verification-key-file", policy_vkey
        ])
    policyKeyHash = policyKeyHash.decode("utf-8").split("\n")[0]
    policyStr = "{\n\t\"keyHash\": \""+policyKeyHash+"\","\
        "\n\t\"type\": \"sig\"\n}"

    policy_script_file = open(policy_script, 'w')
    policy_script_file.write(policyStr)
    policy_script_file.close()
    os.system("cardano-cli transaction policyid " \
            "--script-file "+policy_script +""\
            "> "+policy_id)
    policy_id_val = open(policy_id,'r').readlines()[0].split("\n")[0]
    return policy_id_val, policy_script, policy_skey

def signTransaction(policySkey):
    raw_mat="raw_mat.raw"
    sign_mat="mat.signed"
    vaultSkey="Keys/GameTokenPayment.skey"
    sign = subprocess.check_output([
        CARDANO_CLI_PATH,
        'transaction',
        'sign',
        '--signing-key-file',
        vaultSkey,
        '--signing-key-file',
        policySkey,
        '--testnet-magic',
        str(CARDANO_NETWORK_MAGIC),
        '--tx-body-file',
        raw_mat,
        '--out-file',
        sign_mat,
        ])
    return sign_mat 

def submitTransaction(signed_transaction):
    submit = subprocess.check_output([
        CARDANO_CLI_PATH,
        'transaction',
        'submit',
        "--tx-file",
        signed_transaction,
        "--testnet-magic",
        str(CARDANO_NETWORK_MAGIC)
        ])
    os.system(submit)

def buildToken(
        receiveAddress,
        tokenName,
        tokenAmount):
    policyId, policy_script, policy_skey = buildPolicy(tokenName)
    tokenCommand = "echo -n "+str(tokenName)+" | xxd -ps -c 80 | tr -d '\n'"
    tokenNameHex = os.popen(tokenCommand).read()
    txHash, txix, funds = queryUTXOTop(PHEIDON_CHEST)
    fee = 0
    adaAmount = 2000000
    returnAmount = int(funds) - adaAmount
    command = ""
    command += "cardano-cli transaction build-raw "
    command += "--fee 0 "
    command += "--tx-in "+txHash+"#"+txix+" "
    command += "--tx-out "+receiveAddress+"+"+str(adaAmount)+"+\""
    command += ""+str(tokenAmount)+" "+str(policyId)+"."+str(tokenNameHex)+"\" "
    command += "--tx-out "+BUILDER_ADDRESS+"+"+str(returnAmount)+" " 
    command += "--mint=\""+str(tokenAmount)+" "+policyId+"."+tokenNameHex+"\" " 
    command += "--minting-script-file "+policy_script +" " 
    command += "--out-file raw_mat.raw"
    os.system(command)
    fee = computeFee("raw_mat.raw")
    returnAmount = int(funds) - (fee + adaAmount)
    print(returnAmount)
    print("funds:",
        funds, "=", "adaAmount:",
        adaAmount, "+ fee:", fee,
        " + returnAmount:", returnAmount)
    command = ""
    command += "cardano-cli transaction build-raw "
    command += "--fee "+str(fee)+" "
    command += "--tx-in "+txHash+"#"+txix+" "
    command += "--tx-out "+receiveAddress+"+"+str(adaAmount)+"+\""
    command += ""+str(tokenAmount)+" "+str(policyId)+"."+str(tokenNameHex)+"\" "
    command += "--tx-out "+BUILDER_ADDRESS+"+"+str(returnAmount)+" " 
    command += "--mint=\""+str(tokenAmount)+" "+policyId+"."+tokenNameHex+"\" " 
    command += "--minting-script-file "+policy_script +" " 
    command += "--out-file raw_mat.raw"
    os.system(command)
    signedTransaction = signTransaction(policy_skey)
    submitTransaction(signedTransaction)


    

if __name__=="__main__":
    buildToken(
            receiveAddress=POSEIDON,
            tokenName="Odin",
            tokenAmount=3)
