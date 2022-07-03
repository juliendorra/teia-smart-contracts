"""Unit tests for the Minter contract class.

"""

import smartpy as sp

# Import the fa2 and minter contract modules
fa2Module = sp.io.import_script_from_url("file:contracts/fa2.py")
minterModule = sp.io.import_script_from_url("file:contracts/minter.py")


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")

    # Initialize the extended FA2 contract
    fa2 = fa2Module.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    scenario += fa2

    # Initialize the minter contract
    minter = minterModule.Minter(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"),
        fa2=fa2.address)
    scenario += minter

    # Set the minter contract as the admin of the FA2 contract
    fa2.transfer_administrator(minter.address).run(sender=admin)
    minter.accept_fa2_administrator().run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "fa2": fa2,
        "minter": minter}

    return testEnvironment


@sp.add_test(name="Test mint multiple")
def test_mint_multiple():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]

    # Check that a normal user can mint
    editions = 1
    data = {
        "base": sp.utils.bytes_of_string("ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/"),
    }
    metadata = {
        "1": sp.utils.bytes_of_string("name1"),
        "2": sp.utils.bytes_of_string("name2"),
    }
    royalties = 100
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=user1)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions)
    scenario.verify(fa2.data.ledger[(user1.address, 1)] == editions)
    scenario.verify(fa2.data.supply[0] == editions)
    scenario.verify(fa2.data.supply[1] == editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[1].token_id == 1)

    # Check that the metadata URL returned is a combination of base and name
    scenario.verify(fa2.token_metadata(
        0).token_info[""] == data["base"]+metadata["1"])
    scenario.verify(fa2.token_metadata(
        1).token_info[""] == data["base"]+metadata["2"])

    # Check that the base URL is *not* stored in data, as we want to store it only once in collection
    scenario.verify(~(fa2.data.token_data.contains(0)))
    scenario.verify(~(fa2.data.token_data.contains(1)))

    scenario.verify(fa2.token_royalties(0).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(0).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(1).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(1).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(0).creator.address == user1.address)
    scenario.verify(fa2.token_royalties(0).creator.royalties == royalties)
    scenario.verify(fa2.token_royalties(1).creator.address == user1.address)
    scenario.verify(fa2.token_royalties(1).creator.royalties == royalties)

    # Check that trying to mint a token with zero editions fails
    minter.mint(
        editions=0,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Check that trying to set very hight royalties fails
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=300).run(valid=False, sender=user1)


@sp.add_test(name="Test transfer and accept administrator")
def test_transfer_and_accept_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    minter = testEnvironment["minter"]

    # Check the original administrator
    scenario.verify(minter.data.administrator == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = user1.address
    minter.transfer_administrator(
        new_administrator).run(valid=False, sender=user1)
    minter.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(
        minter.data.proposed_administrator.open_some() == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    minter.accept_administrator().run(valid=False, sender=admin)
    minter.accept_administrator().run(sender=user1)

    # Check that the administrator is updated
    scenario.verify(minter.data.administrator == new_administrator)
    scenario.verify(~minter.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = user2.address
    minter.transfer_administrator(
        new_administrator).run(valid=False, sender=admin)
    minter.transfer_administrator(new_administrator).run(sender=user1)

    # Check that the proposed administrator is updated
    scenario.verify(
        minter.data.proposed_administrator.open_some() == new_administrator)


@sp.add_test(name="Test transfer and accept FA2 administrator")
def test_transfer_and_accept_fa2_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]

    # Initialize a new minter contract and add it to the test scenario
    new_minter = minterModule.Minter(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        fa2=fa2.address)
    scenario += new_minter

    # Check the original FA2 token administrator
    scenario.verify(fa2.data.administrator == minter.address)

    # Propose the new FA2 token contract administrator
    minter.transfer_fa2_administrator(
        new_minter.address).run(valid=False, sender=user1)
    minter.transfer_fa2_administrator(new_minter.address).run(sender=admin)

    # Accept the new FA2 token contract administrator responsabilities
    new_minter.accept_fa2_administrator().run(valid=False, sender=user1)
    new_minter.accept_fa2_administrator().run(sender=admin)

    # Check that the administrator has been updated
    scenario.verify(fa2.data.administrator == new_minter.address)

    # Check that minting with the old minter fails
    editions = 5
    data = {
        "base": sp.utils.bytes_of_string("ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/"),
    }
    metadata = {
        "1": sp.utils.bytes_of_string("name1"),
        "2": sp.utils.bytes_of_string("name2"),
    }
    royalties = 100
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Check that it's possible to mint with the new minter
    new_minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=user1)


@sp.add_test(name="Test set pause")
def test_set_pause():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    minter = testEnvironment["minter"]

    # Pause the contract
    minter.set_pause(True).run(valid=False, sender=user1)
    minter.set_pause(True).run(sender=admin)

    # Check that the contract is paused
    scenario.verify(minter.data.paused)
    scenario.verify(minter.is_paused())

    # Check that minting fails
    editions = 5
    data = {
        "base": sp.utils.bytes_of_string("ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/"),
    }
    metadata = {
        "1": sp.utils.bytes_of_string("name1"),
        "2": sp.utils.bytes_of_string("name2"),
    }
    royalties = 100
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Unpause the contract
    minter.set_pause(False).run(valid=False, sender=user1)
    minter.set_pause(False).run(sender=admin)

    # Check that the contract is not paused
    scenario.verify(~minter.data.paused)
    scenario.verify(~minter.is_paused())

    # Check that minting is possible again
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=user1)
