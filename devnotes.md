test fa2 contract:
cd python
~/smartpy-cli/SmartPy.sh test tests/fa2_test.py ../output/tests/fa2 --html --purge
~/smartpy-cli/SmartPy.sh test tests/minter_test.py ../output/tests/minter --html --purge

### off chain views for FA2: metadata file

If you made any changes to the views in FA2 contract : 

 - update the "views": [...] array in contract_metadata = {...} object

 - compile the contract once
  ~/smartpy-cli/SmartPy.sh compile python/contracts/fa2.py output/contracts/fa2 --html --purge

 - upload step_000_cont_0_metadata.contract_metadata.json to IPFS, note ipfs link (ipfs://[CID])
  
 - add ipfs link to FA2 compilation target metadata
  
 - compile again 
  
-  deploy

### deploy / originate contracts

~/smartpy-cli/SmartPy.sh compile python/contracts/fa2.py output/contracts/fa2 --html --purge

~/smartpy-cli/SmartPy.sh originate-contract --code output/contracts/fa2/fa2/step_000_cont_0_contract.json --storage output/contracts/fa2/fa2/step_000_cont_0_storage.json --rpc https://rpc.ghostnet.teztnets.xyz

Once originated, change the FA2 contract address in the Minter contract, compile, then deploy :

~/smartpy-cli/SmartPy.sh compile python/contracts/minter.py output/contracts/minter --html --purge

~/smartpy-cli/SmartPy.sh originate-contract --code output/contracts/minter/minter/step_000_cont_0_contract.json --storage output/contracts/minter/minter/step_000_cont_0_storage.json --rpc https://rpc.ghostnet.teztnets.xyz

### addresses 

tz1ahsDNFzukj51hVpW626qH7Ug9HeUVQDNG ithacanet testnet account
Use it in fa2.py and minter.py as the administrator address

FA2 contract on ithacanet: KT1SBUCG4B7qzW17HpMJmLFk4twpn3sYQked
Use it in minter.py as fa2 contract

Minter contract on ithacanet:  KT1GiJKFFECRF5cxrqVYu9Wmioxp5D8nSVvd
Call it from Taquito !!


After Deploying the contracts, we need to set the minter contract as the admin of the FA2 contract. 
Only the admin can mint tokens. That's why the minter contract should be the admin

We cannot set it at once when deploying because we would a circular dependency: 
the minter contract needs to know the FA2 address, and the FA2 contract need the minter address as admin…


# Set the minter contract as the admin of the FA2 contract
# both contracts have to be called by their current admin for the change to be final
fa2.transfer_administrator(minter.address).run(sender=admin)
minter.accept_fa2_administrator().run(sender=admin)

using Taquito it can be batched as one operation done after authenticating with the admin wallet:

  const batch = await Tezos.wallet.batch()
            .withContractCall(
                FA2Contract.methods.transfer_administrator(MINTER)
            )
            .withContractCall(
                minterContract.methods.accept_fa2_administrator()
            )

        const batchOperation = await batch.send()


And here's the results on testnet:
https://ithacanet.tzkt.io/ongG4CUp9qTh9fupshKBUihQqNGUjpR3Tgeq12wok1W68ohv2aX


//////////////

The data parameter is to store some data associated with the token on-chain. Some people might want include some text on-chain, some source code, etc


to call the minter from Taquito

    const metadataUrlAsBytes = char2Bytes(
        "ipfs://" + metadataUrl)

    // {
    //     "editions": "nat",
    //     "metadata": {
    //       "map": {
    //         "key": "string",
    //         "value": "bytes"
    //       }
    //     },
    //     "data": {
    //       "map": {
    //         "key": "string",
    //         "value": "bytes"
    //       }
    //     },
    //     "royalties": "nat"
    //   }

    const metadataMap = new MichelsonMap();
    metadataMap.set("", metadataUrlAsBytes);

    const emptyMap = new MichelsonMap();


    const params = {
        "editions": 1,
        "metadata": metadataMap,
        "data": emptyMap,
        "royalties": 100
    }

    try {
        const contract = await Tezos.wallet.at(MINTER)

        const op = await contract.methodsObject
            .mint(params)
            .send()

        await op.confirmation()

        if (await op.status() === "applied") {
            console.log("Success!")
        } else {
            throw `Transaction error: ${await op.status()}`
        }
    } catch (error) {
        console.log(error);
    }

