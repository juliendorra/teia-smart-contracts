"""Unit tests for the FA2 class.

"""

import smartpy as sp

# Import the fa2 contract module
fa2Module = sp.io.import_script_from_url("file:contracts/fa2.py")


class Dummy(sp.Contract):
    """This dummy contract implements a callback method to receive the token
    balance information.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            balances=sp.TBigMap(sp.TPair(sp.TAddress, sp.TNat), sp.TNat)))

        # Initialize the contract storage
        self.init(balances=sp.big_map())

    @sp.entry_point
    def receive_balances(self, params):
        """Callback entry point that receives the token balance information.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TRecord(
            request=sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")),
            balance=sp.TNat).layout(("request", "balance"))))

        # Save the returned information in the balances big map
        with sp.for_("balance_info", params) as balance_info:
            request = balance_info.request
            self.data.balances[
                (request.owner, request.token_id)] = balance_info.balance


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

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "fa2": fa2}

    return testEnvironment


@sp.add_test(name="Test mint multiple")
def test_mint_multiple():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]

    # Check that the admin can mint multiple tokens at once
    editions = 1  # editions are fixed in contract to 1!
    total = 2
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user2.address, royalties=50))
    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)
    scenario.verify(fa2.total_supply(1) == editions)

    # Check that the metadata URL returned is a combination of base and name
    scenario.verify(fa2.token_metadata(
        0).token_info[""] == base+sp.utils.bytes_of_string("0"))
    scenario.verify(fa2.token_metadata(
        1).token_info[""] == base+sp.utils.bytes_of_string("1"))

    scenario.verify(fa2.token_royalties(0).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(0).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(0).creator.address == user2.address)
    scenario.verify(fa2.token_royalties(0).creator.royalties == 50)
    scenario.verify(fa2.token_royalties(1).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(1).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(1).creator.address == user2.address)
    scenario.verify(fa2.token_royalties(1).creator.royalties == 50)
    scenario.verify(fa2.token_exists(0))
    scenario.verify(fa2.token_exists(1))
    scenario.verify(~fa2.token_exists(2))
    scenario.verify(~fa2.token_exists(3))
    scenario.verify(fa2.last_token_id() == 1)
    scenario.verify(sp.len(fa2.all_tokens()) == 2)


@sp.add_test(name="Test collection views")
def test_collection_views():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]

    # check that empty contract views fail

    collection_range = sp.record(
        start=0,
        end=0)

    sp.is_failing(fa2.last_token_id())
    sp.is_failing(fa2.last_collection_id())
    sp.is_failing(fa2.all_collections())
    sp.is_failing(fa2.list_collection_cids(collection_range))

    # mint 2 collections of 256 tokens
    editions = 1  # editions are fixed in contract to 1!
    total = 256
    base = []
    base.append(sp.utils.bytes_of_string(
        "ipfs://bafybeig6n47ha7iww6nawplbpk5unvrgyjdbbaqfm4sslgkx3xxbvv43pu/"))
    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user1.address, royalties=50))
    fa2.mint_collection(
        total=total,
        base=base[0],
        royalties=royalties).run(sender=admin)
    base.append(sp.utils.bytes_of_string(
        "ipfs://bafybeia2il256fmpk4tlgan57qxnxpqitlwwm2bg6ia3brvijw2ierq33q/"))
    fa2.mint_collection(
        total=total,
        base=base[1],
        royalties=royalties).run(sender=admin)

    # Check that the contract information has been updated
    # first token minted
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)
    # last token minted
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=511)) == editions)
    scenario.verify(fa2.total_supply(511) == editions)

    # Check that the metadata URL returned is a combination of base and name
    scenario.verify(fa2.token_metadata(
        0).token_info[""] == base[0]+sp.utils.bytes_of_string("0"))

    # test the second token of the second collection (from 256 to 511)
    scenario.verify(fa2.token_metadata(
        257).token_info[""] == base[1]+sp.utils.bytes_of_string("1"))

    """
                fa2.last_token_id,
                fa2.last_collection_id,
                fa2.all_collections,
                fa2.list_collection_cids,
                fa2.collection_first_last_tokens,
    """

    # checking that collection counter has been properly updated
    scenario.verify(fa2.data.collection_counter == 2)

    scenario.verify(fa2.last_token_id() == 511)
    scenario.verify(fa2.last_collection_id() == 1)
    scenario.verify_equal(fa2.all_collections(), [0, 1])

    # checking that we can list cids for collections

    collection_range = sp.record(start=0, end=1)

    single_collection_range = sp.record(start=1, end=1)

    wrong_collection_range = sp.record(
        start=3,
        end=3)

    inverted_collection_range = sp.record(
        start=1,
        end=0)

    collection_cids = fa2.list_collection_cids(collection_range)

    scenario.verify(sp.len(collection_cids) == 2)

    scenario.verify(collection_cids.contains(
        sp.record(collectionid=0, cid=base[0]))
    )

    scenario.verify(collection_cids.contains(
        sp.record(collectionid=1, cid=base[1]))
    )

    collection_cid_single = fa2.list_collection_cids(single_collection_range)

    scenario.verify(sp.len(collection_cid_single) == 1)

    scenario.verify(collection_cid_single.contains(
        sp.record(collectionid=1, cid=base[1]))
    )

    sp.is_failing(~fa2.list_collection_cids(wrong_collection_range))
    sp.is_failing(~fa2.list_collection_cids(inverted_collection_range))

    # checkin that we can get the first and last token id of a collection
    # collection 0: first=0,last=255

    scenario.verify(fa2.collection_first_last_tokens(0).first == 0)
    scenario.verify(fa2.collection_first_last_tokens(0).last == 255)

    scenario.verify(fa2.collection_first_last_tokens(1).first == 256)
    scenario.verify(fa2.collection_first_last_tokens(1).last == 511)

    sp.is_failing(fa2.collection_first_last_tokens(3))


@sp.add_test(name="Test collection transfer")
def test_collection_transfer():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # check that transfer on empty contract fail
    fa2.transfer_collection(
        sp.record(
            from_=user1.address,
            to_=user1.address,
            collection_id=0
        )
    ).run(valid=False, sender=user1)

    # mint 2 collections of 256 tokens
    editions = 1  # editions are fixed in contract to 1!
    total = 256

    base = []

    base.append(sp.utils.bytes_of_string(
        "ipfs://bafybeig6n47ha7iww6nawplbpk5unvrgyjdbbaqfm4sslgkx3xxbvv43pu/"))
    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user1.address, royalties=50))

    fa2.mint_collection(
        total=total,
        base=base[0],
        royalties=royalties).run(sender=admin)

    base.append(sp.utils.bytes_of_string(
        "ipfs://bafybeia2il256fmpk4tlgan57qxnxpqitlwwm2bg6ia3brvijw2ierq33q/"))
    fa2.mint_collection(
        total=total,
        base=base[1],
        royalties=royalties).run(sender=admin)

    # Check that we can transfer collection to another user
    fa2.transfer_collection(
        sp.record(
            from_=user1.address,
            to_=user2.address,
            collection_id=0
        )
    ).run(sender=user1)

    # Check that the contract information has been updated
    # And user2 is the new owner of the collection

    for i in range(0, 255):
        scenario.verify(fa2.get_balance(
            sp.record(owner=user2.address, token_id=i)) == editions)

    # Check that another user cannot transfer a collection
    fa2.transfer_collection(
        sp.record(
            from_=user1.address,
            to_=user3.address,
            collection_id=0
        )
    ).run(valid=False, sender=user1)

    # Check that the collection owner can transfer one token
    # Token 278 is from collection with id 1
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=278, amount=editions)])
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=278)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=278)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that collection transfer is now impossible
    # as the collection is not fresh anymore
    # but part lazy ledger, part traditional ledger
    fa2.transfer_collection(
        sp.record(
            from_=user1.address,
            to_=user3.address,
            collection_id=1
        )
    ).run(valid=False, sender=user1)


@ sp.add_test(name="Test transfer")
def test_transfer():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Mint a token
    editions = 1  # editions are fixed in contract to 1
    total = 1
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user2.address, royalties=50))
    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that the creator cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=editions)])
    ]).run(valid=False, sender=user2)

    # Check that another user cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=editions)])
    ]).run(valid=False, sender=user3)

    # Check that the admin cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=editions)])
    ]).run(valid=False, sender=admin)

    # Check that the owner can transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=editions)])
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that the owner cannot transfer more tokens than the ones they have
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
    ]).run(valid=False, sender=user1)

    # Check that an owner cannot transfer other owners editions
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)])
    ]).run(valid=False, sender=user3)

    # Check that the new owner can transfer their own editions
    fa2.transfer([
        sp.record(
            from_=user3.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=editions)])
    ]).run(sender=user3)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == editions)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.total_supply(0) == editions)

    # Make the first user as operator of the second user newly transfered token
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user2.address,
        operator=user1.address,
        token_id=0))]).run(sender=user2)

    # Check that the first user now can transfer the user2 token
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=editions)])
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)


@ sp.add_test(name="Test complex transfer")
def test_complex_transfer():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Mint two tokens
    total = 1
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")

    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user1.address, royalties=100))

    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    royalties = sp.record(
        minter=sp.record(address=user2.address, royalties=0),
        creator=sp.record(address=user2.address, royalties=100))

    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == 1)

    scenario.verify(fa2.total_supply(0) == 1)
    scenario.verify(fa2.total_supply(1) == 1)

    # Check that users can only transfer tokens they own
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=1)])
    ]).run(valid=False, sender=user3)

    # Check that the contract information hasn't changed
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=1)) == 0)

    # Check that the admin cannot transfer whatever token they want
    fa2.transfer([
        sp.record(
            from_=user3.address,
            txs=[sp.record(to_=user1.address, token_id=0, amount=1)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=1)])
    ]).run(valid=False, sender=admin)

    # Check that transfer over 1 fails
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user1.address, token_id=0, amount=2)])
    ]).run(valid=False, sender=user1)

    # Check that the contract information hasn't changed
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=1)) == 0)

    # Check that owners can transfer tokens to themselves
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user2.address, token_id=1, amount=1)])
    ]).run(sender=user2)

    # Check that the contract information hasn't changed
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=1)) == 0)

    # Make the user 3 as operator of user 2 token: id 1
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user2.address,
        operator=user3.address,
        token_id=1))]).run(sender=user2)

    # Transfer user 1 token: id 0 to user 3
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)])
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=1)) == 0)

    # Check that user 3 can transfer their token (id 0) and the user 2 token (id 1)
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user1.address, token_id=1, amount=1)]),
        sp.record(
            from_=user3.address,
            txs=[sp.record(to_=user1.address, token_id=0, amount=1)])
    ]).run(sender=user3)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == 1)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=1)) == 0)


@ sp.add_test(name="Test balance of")
def test_balance_of():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Intialize the dummy contract and add it to the test scenario
    dummyContract = Dummy()
    scenario += dummyContract

    # Get the contract handler to the receive_balances entry point
    c = sp.contract(
        t=sp.TList(sp.TRecord(
            request=sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")),
            balance=sp.TNat).layout(("request", "balance"))),
        address=dummyContract.address,
        entry_point="receive_balances").open_some()

    # Mint two tokens
    editions = 1  # editions are fixed in contract to 1
    total = 1
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")

    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user1.address, royalties=100))
    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    royalties = sp.record(
        minter=sp.record(address=user2.address, royalties=0),
        creator=sp.record(address=user2.address, royalties=100))
    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    # Check the balances using the on-chain view
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=1)) == editions)

    # Check that it doesn't fail if there is not row for that information in the ledger
    scenario.verify(fa2.get_balance(
        sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user1.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=user3.address, token_id=1)) == 0)

    # Check that it fails if the token doesn't exist
    scenario.verify(sp.is_failing(fa2.get_balance(
        sp.record(owner=user1.address, token_id=10))))

    # Check that asking for the token balances fails if the token doesn't exist
    fa2.balance_of(sp.record(
        requests=[sp.record(owner=user1.address, token_id=10)],
        callback=c)).run(valid=False, sender=user3)

    # Ask for the token balances
    fa2.balance_of(sp.record(
        requests=[
            sp.record(owner=user1.address, token_id=0),
            sp.record(owner=user2.address, token_id=0),
            sp.record(owner=user3.address, token_id=0),
            sp.record(owner=user1.address, token_id=1),
            sp.record(owner=user2.address, token_id=1),
            sp.record(owner=user3.address, token_id=1)],
        callback=c)).run(sender=user3)

    # Check that the returned balances are correct
    scenario.verify(dummyContract.data.balances[(user1.address, 0)] == 1)
    scenario.verify(dummyContract.data.balances[(user2.address, 0)] == 0)
    scenario.verify(dummyContract.data.balances[(user3.address, 0)] == 0)
    scenario.verify(dummyContract.data.balances[(user1.address, 1)] == 0)
    scenario.verify(dummyContract.data.balances[(user2.address, 1)] == 1)
    scenario.verify(dummyContract.data.balances[(user3.address, 1)] == 0)


@ sp.add_test(name="Test update operators")
def test_update_operators():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Mint two tokens with two different owners
    editions = 1  # editions are fixed in contract to 1
    total = 1
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")

    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user1.address, royalties=100))
    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    royalties = sp.record(
        minter=sp.record(address=user2.address, royalties=0),
        creator=sp.record(address=user2.address, royalties=100))
    fa2.mint_collection(
        total=total,
        base=base,
        royalties=royalties).run(sender=admin)

    # Check that the operators information is empty
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user2.address, operator=user1.address, token_id=1)))

    # Check that is not possible to change the operators if one is not the owner
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user2)
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user3)

    # Check that the admin cannot add operators
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=admin)

    # Check that the user can change the operators of token they own or might
    # own in the future
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=1)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=1))
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=1)))

    # Check that adding and removing operators works at the same time
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=1)),
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=1)),
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=1)))

    # Check that removing an operator that doesn't exist works
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0)),
    ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))

    # Check operators cannot change the operators of editions that they don't own
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0))]).run(valid=False, sender=user2)
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user2)

    # Check that the admin cannot remove operators
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=admin)


@ sp.add_test(name="Test transfer and accept administrator")
def test_transfer_and_accept_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]

    # Check the original administrator
    scenario.verify(fa2.data.administrator == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = user1.address
    fa2.transfer_administrator(new_administrator).run(
        valid=False, sender=user1)
    fa2.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(fa2.data.proposed_administrator.open_some()
                    == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    fa2.accept_administrator().run(valid=False, sender=admin)
    fa2.accept_administrator().run(sender=user1)

    # Check that the administrator is updated
    scenario.verify(fa2.data.administrator == new_administrator)
    scenario.verify(~fa2.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = user2.address
    fa2.transfer_administrator(new_administrator).run(
        valid=False, sender=admin)
    fa2.transfer_administrator(new_administrator).run(sender=user1)

    # Check that the proposed administrator is updated
    scenario.verify(fa2.data.proposed_administrator.open_some()
                    == new_administrator)


@ sp.add_test(name="Test set metadata")
def test_set_metadata():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]

    # Check that only the admin can update the metadata
    new_metadata = sp.record(k="", v=sp.utils.bytes_of_string("ipfs://zzzz"))
    fa2.set_metadata(new_metadata).run(valid=False, sender=user1)
    fa2.set_metadata(new_metadata).run(sender=admin)

    # Check that the metadata is updated
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)

    # Add some extra metadata
    extra_metadata = sp.record(
        k="aaa", v=sp.utils.bytes_of_string("ipfs://ffff"))
    fa2.set_metadata(extra_metadata).run(sender=admin)

    # Check that the two metadata entries are present
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)
    scenario.verify(fa2.data.metadata[extra_metadata.k] == extra_metadata.v)
