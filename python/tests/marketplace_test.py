"""Unit tests for the Marketplace contract class.

"""

import os
import smartpy as sp

# Import the fa2, minter and marketplace contract modules
fa2Module = sp.io.import_script_from_url("file:contracts/fa2.py")
minterModule = sp.io.import_script_from_url("file:contracts/minter.py")
marketplaceModule = sp.io.import_script_from_url(
    "file:contracts/marketplace.py")


class Recipient(sp.Contract):
    """This contract simulates a user that can receive tez transfers.

    It should only be used to test that tez transfers are sent correctly.

    """

    def __init__(self):
        """Initializes the contract.

        """
        self.init()

    @sp.entry_point
    def default(self, unit):
        """Default entrypoint that allows receiving tez transfers in the same
        way as one would do with a normal tz wallet.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Do nothing, just receive tez
        pass


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    collector1 = sp.test_account("collector1")
    collector2 = sp.test_account("collector2")

    # Initialize the artists contracts that will receive the royalties
    artist1 = Recipient()
    artist2 = Recipient()
    scenario += artist1
    scenario += artist2

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

    # Initialize the marketplace contract
    marketplace = marketplaceModule.Marketplace(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        fa2=fa2.address,
        fee=sp.nat(25))
    scenario += marketplace

    # Initialize the fee recipient contract
    fee_recipient = Recipient()
    scenario += fee_recipient

    # Set the minter contract as the admin of the FA2 contract
    fa2.transfer_administrator(minter.address).run(sender=admin)
    minter.accept_fa2_administrator().run(sender=admin)

    # Change the marketplace fee recipient
    marketplace.update_fee_recipient(fee_recipient.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "artist1": artist1,
        "artist2": artist2,
        "collector1": collector1,
        "collector2": collector2,
        "fa2": fa2,
        "minter": minter,
        "marketplace": marketplace,
        "fee_recipient": fee_recipient}

    return testEnvironment


@sp.add_test(name="Test swap and collect")
def test_swap_and_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    fee = sp.nat(25)

    #  Mint a collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist2.address)

    token_id = 178
    price = sp.mutez(25*1000000)

    # Add the marketplace contract as token operator to be able to swap it
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist2.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist2.address)

    scenario.verify(marketplace.data.counter == 0)

    # Check that there are no active swap for token
    scenario.verify(~marketplace.data.swaps.contains(token_id))
    scenario.verify(~marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swaps_counter() == 0)

    # Check that tez transfers are not allowed when swapping
    swapped_editions = 1

    marketplace.swap(
        token_id=token_id,
        price=price).run(valid=False, sender=artist2.address, amount=sp.tez(3))

    # Swap the token on the marketplace contract
    marketplace.swap(
        token_id=token_id,
        price=price).run(sender=artist2.address)

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist2.address))
    scenario.verify(
        fa2.data.ledger[token_id] == marketplace.address)

    # Check that the swaps big map is correct
    scenario.verify(marketplace.data.swaps.contains(token_id))
    scenario.verify(marketplace.data.swaps[token_id].issuer == artist2.address)
    scenario.verify(marketplace.data.swaps[token_id].token_id == token_id)
    scenario.verify(
        marketplace.data.swaps[token_id].editions == swapped_editions)
    scenario.verify(marketplace.data.swaps[token_id].price == price)
    scenario.verify(marketplace.data.counter == 1)
    scenario.verify(marketplace.data.highest_token_swapped == token_id)

    # Check that the on-chain views work
    scenario.verify(marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swap(token_id).issuer == artist2.address)
    scenario.verify(marketplace.get_swap(token_id).token_id == token_id)
    scenario.verify(marketplace.get_swap(
        token_id).editions == swapped_editions)
    scenario.verify(marketplace.get_swap(token_id).price == price)
    scenario.verify(marketplace.get_swaps_counter() == 1)

    ##
    # Collecting the single swapped token
    ##

    # Check that collecting fails if the collector is the swap issuer
    marketplace.collect(token_id).run(
        valid=False, sender=artist2.address, amount=price)

    # Check that collecting fails if the exact tez amount is not provided
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=(price - sp.mutez(1)))
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=(price + sp.mutez(1)))

    # Collect token with collector 1
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))

    # sp.split_tokens(amount, quantity, totalQuantity)
    # amount * quantity / totalQuantity
    # calculate in per mille

    # marketplace had 1 sale at price, should get fee/1000 of price
    scenario.verify(fee_recipient.balance == sp.split_tokens(price, fee, 1000))

    # artist2 had 1 primary sale at price, get price - fees
    scenario.verify(artist2.balance == price
                    - sp.split_tokens(price, fee, 1000))

    scenario.verify(marketplace.data.swaps[token_id].editions == 0)
    sp.is_failing(~marketplace.get_swap(token_id))

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist2.address))
    scenario.verify(
        ~(fa2.data.ledger[token_id] == marketplace.address))


@sp.add_test(name="Test swap and cancel swap")
def test_swap_and_cancel_swap():
    # Get the test environment

    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    #  Mint a collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist2.address)

    token_id = 255
    price = sp.mutez(25*1000000)

    # Add the marketplace contract as an operator to be able to swap it
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist2.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist2.address)

    # Check that there are no active swap for token
    scenario.verify(~marketplace.data.swaps.contains(token_id))
    scenario.verify(~marketplace.has_swap(token_id))
    scenario.verify(marketplace.data.counter == 0)
    scenario.verify(marketplace.get_swaps_counter() == 0)

    # Check that tez transfers are not allowed when swapping
    swapped_editions = 1

    marketplace.swap(
        token_id=token_id,
        price=price).run(valid=False, sender=artist2.address, amount=sp.tez(3))

    # Swap the token on the marketplace contract
    marketplace.swap(
        token_id=token_id,
        price=price).run(sender=artist2.address)

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist2.address))
    scenario.verify(
        fa2.data.ledger[token_id] == marketplace.address)

    # Check that the swaps big map is correct
    scenario.verify(marketplace.data.swaps.contains(token_id))
    scenario.verify(marketplace.data.swaps[token_id].issuer == artist2.address)
    scenario.verify(marketplace.data.swaps[token_id].token_id == token_id)
    scenario.verify(
        marketplace.data.swaps[token_id].editions == swapped_editions)
    scenario.verify(marketplace.data.swaps[token_id].price == price)
    scenario.verify(marketplace.data.counter == 1)
    scenario.verify(marketplace.data.highest_token_swapped == token_id)

    # Check that the on-chain views work
    scenario.verify(marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swap(token_id).issuer == artist2.address)
    scenario.verify(marketplace.get_swap(token_id).token_id == token_id)
    scenario.verify(marketplace.get_swap(
        token_id).editions == swapped_editions)
    scenario.verify(marketplace.get_swap(token_id).price == price)
    scenario.verify(marketplace.get_swaps_counter() == 1)

    # Check that only the swapper can cancel the swap
    marketplace.cancel_swap(token_id).run(valid=False, sender=collector1)
    marketplace.cancel_swap(token_id).run(sender=artist2.address)

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == marketplace.address))
    scenario.verify(fa2.data.ledger[token_id] == artist2.address)

    # Check that the swaps big map has been updated
    # the map still holds a 0-edition swap
    scenario.verify(marketplace.data.swaps.contains(token_id))
    # but the views return correctly that the swap is not in effect
    scenario.verify(~marketplace.has_swap(token_id))
    sp.is_failing(~marketplace.get_swap(token_id))

    scenario.verify(marketplace.get_swaps_counter() == 1)

    # Check that the swap cannot be cancelled twice
    marketplace.cancel_swap(token_id).run(valid=False, sender=artist2.address)


@sp.add_test(name="Test swap and collect using collection swap")
def test_swap_and_collect_using_collection_swap():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    fee = sp.nat(25)

    #  Mint a collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    ##
    # Swap the whole fresh collection to the marketplace
    ##

    # First, add the marketplace contract as an operator of the collection

    collection_id = 0
    fa2.update_collection_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        collection_id=collection_id))]).run(sender=artist1.address)

    # check that trying to assign price to too many tokens fails
    marketplace.swap_collection(
        collection_id=collection_id,
        price_list=sp.list(
            [sp.record(
                quantity=100,
                price=sp.mutez(3*1000000)),
             sp.record(
                quantity=100,
                price=sp.mutez(7*1000000)),
             sp.record(
                quantity=57,
                price=sp.mutez(15*1000000)),
             ]
        )
    ).run(valid=False, sender=artist1.address)

    # check that trying to assign price to too few tokens also fails
    marketplace.swap_collection(
        collection_id=collection_id,
        price_list=sp.list(
            [sp.record(
                quantity=100,
                price=sp.mutez(3*1000000)),
             sp.record(
                quantity=100,
                price=sp.mutez(10*1000000)),
             sp.record(
                quantity=55,
                price=sp.mutez(25*1000000)),
             ]
        )
    ).run(valid=False, sender=artist1.address)

    # Swap with exact total quantity in price list
    marketplace.swap_collection(
        collection_id=collection_id,
        price_list=sp.list(
            [sp.record(
                quantity=100,
                price=sp.mutez(3*1000000)),
             sp.record(
                quantity=100,
                price=sp.mutez(10*1000000)),
             sp.record(
                quantity=56,
                price=sp.mutez(25*1000000)),
             ]
        )
    ).run(sender=artist1.address)

    # remove the marketplace contract as an operator of the collection
    fa2.update_collection_operators([sp.variant("remove_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        collection_id=collection_id))]).run(sender=artist1.address)

    # Check that there is a collection swap in the marketplace
    scenario.verify(marketplace.data.collection_swaps_counter == 1)
    scenario.verify(marketplace.data.highest_token_swapped == 255)
    scenario.verify(marketplace.get_collection_swaps_counter() == 1)

    # check prices for the tokens
    # from swap infos
    #   issuer
    #   token_id
    #   editions
    #   price

    # check price for token 0 to 99 = 100 tokens
    # remember that range() is [start, endexclusive)
    for i in range(0, 100):
        scenario.verify(marketplace.get_swap(i).price == sp.mutez(3*1000000))

    # check price for token 100 to 199 = 100 tokens
    for i in range(100, 200):
        scenario.verify(marketplace.get_swap(i).price == sp.mutez(10*1000000))

    # check price for token 200 to 255 = 56 tokens
    for i in range(200, 256):
        scenario.verify(marketplace.get_swap(i).price == sp.mutez(25*1000000))

    ##
    # Collect from the collection swap
    ##

    token_id = 255
    price = sp.mutez(25*1000000)

    # Check that collecting fails if the collector is the swap issuer
    marketplace.collect(token_id).run(
        valid=False, sender=artist1.address, amount=price)

    # Check that collecting fails if the exact tez amount is not provided
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=(price - sp.mutez(1)))
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=(price + sp.mutez(1)))

    # Collect token 255 with collector 1
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))
    scenario.verify(marketplace.data.swaps[token_id].editions == 0)
    sp.is_failing(~marketplace.get_swap(token_id))

    # sp.split_tokens(amount, quantity, totalQuantity)
    # amount * quantity / totalQuantity
    # calculate in per mille

    # marketplace had 1 sales at price
    scenario.verify(fee_recipient.balance == sp.split_tokens(price, fee, 1000))

    # artist1 had 1 primary sale at price - minus markteplace fee
    scenario.verify(artist1.balance == price
                    - sp.split_tokens(price, fee, 1000))

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist1.address))
    scenario.verify(
        ~(fa2.data.ledger[token_id] == marketplace.address))
    scenario.verify(
        (fa2.data.ledger[token_id] == collector1.address))

    # cancel swap just for token id 15
    token_id = 15
    marketplace.cancel_swap(token_id).run(sender=artist1.address)

    # Check that collecting fails for canceled swap
    marketplace.collect(token_id).run(
        valid=False,
        sender=artist1.address,
        amount=sp.mutez(3*1000000)
    )

    # Transfer token 15 to artist 2 (direct FA2 transfer)
    editions = 1

    fa2.transfer([
        sp.record(
            from_=artist1.address,
            txs=[sp.record(to_=artist2.address, token_id=token_id, amount=editions)])
    ]).run(sender=artist1.address)

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist1.address))
    scenario.verify(
        fa2.data.ledger[token_id] == artist2.address)

    # Add the marketplace contract as an operator to be able to swap it
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist2.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist2.address)

    # Check a single token swap entry has been created internally
    # now taking priority over collection operations
    scenario.verify(marketplace.data.swaps.contains(token_id))

    # Check that this token swap is not active / visible via views
    scenario.verify(~marketplace.has_swap(token_id))
    scenario.verify(marketplace.data.counter == 0)
    scenario.verify(marketplace.get_swaps_counter() == 0)

    # Check that tez transfers are not allowed when swapping
    swapped_editions = 1

    marketplace.swap(
        token_id=token_id,
        price=price).run(valid=False, sender=artist2.address, amount=sp.tez(3))

    # Swap the token on the marketplace contract
    marketplace.swap(
        token_id=token_id,
        price=price).run(sender=artist2.address)

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist2.address))
    scenario.verify(
        fa2.data.ledger[token_id] == marketplace.address)

    # Check that the swaps big map is correct
    scenario.verify(marketplace.data.swaps.contains(token_id))
    scenario.verify(marketplace.data.swaps[token_id].issuer == artist2.address)
    scenario.verify(marketplace.data.swaps[token_id].token_id == token_id)
    scenario.verify(
        marketplace.data.swaps[token_id].editions == swapped_editions)
    scenario.verify(marketplace.data.swaps[token_id].price == price)
    scenario.verify(marketplace.data.counter == 1)
    scenario.verify(marketplace.data.highest_token_swapped == 255)

    # Check that the on-chain views work
    scenario.verify(marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swap(token_id).issuer == artist2.address)
    scenario.verify(marketplace.get_swap(token_id).token_id == token_id)
    scenario.verify(marketplace.get_swap(
        token_id).editions == swapped_editions)
    scenario.verify(marketplace.get_swap(token_id).price == price)
    scenario.verify(marketplace.get_swaps_counter() == 1)

    ##
    # Collecting the single swapped token
    ##

    # Check that collecting fails if the collector is the swap issuer
    marketplace.collect(token_id).run(
        valid=False, sender=artist2.address, amount=price)

    # Check that collecting fails if the exact tez amount is not provided
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=(price - sp.mutez(1)))
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=(price + sp.mutez(1)))

    # Collect token 15 with collector 1
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))

    # sp.split_tokens(amount, quantity, totalQuantity)
    # amount * quantity / totalQuantity
    # calculate in per mille

    # marketplace had 2 sales at price
    scenario.verify(fee_recipient.balance == sp.mul(
        2, sp.split_tokens(price, fee, 1000)))

    # artist1 had 2 sales at price,
    # one primary and one secondary after gifting the token
    # thus their balance is
    # 1 full price - fee
    # + 1 royalty split
    scenario.verify(artist1.balance == price
                    - sp.split_tokens(price, fee, 1000)
                    + sp.split_tokens(price, royalties, 1000))

    # artist2 sold artist1 token on the marketpace
    # gets secondary set sale price minus fees and royalties
    scenario.verify(artist2.balance == price
                    - sp.split_tokens(price, fee, 1000)
                    - sp.split_tokens(price, royalties, 1000))

    # Check a single token swap entry has been created internally
    # now taking priority over collection operations
    scenario.verify(marketplace.data.swaps.contains(token_id))

    # Check that this token swap is not active / visible via views
    scenario.verify(marketplace.data.swaps[token_id].editions == 0)
    scenario.verify(~marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swaps_counter() == 1)
    sp.is_failing(~marketplace.get_swap(token_id))

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist1.address))
    scenario.verify(
        ~(fa2.data.ledger[token_id] == marketplace.address))


@ sp.add_test(name="Test free collect")
def test_free_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    #  Mint a token collection
    editions = 1  # editions are fixed in contract to 1!
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap the token in the marketplace contract for a price of 0 tez
    price = sp.mutez(0)

    marketplace.swap(
        token_id=token_id,
        price=price).run(sender=artist1.address)

    # Collect the token
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))
    scenario.verify(fee_recipient.balance == sp.mutez(0))
    scenario.verify(artist1.balance == sp.mutez(0))
    scenario.verify(marketplace.data.swaps[token_id].editions == 0)

    # Check that the token ledger information is correct
    scenario.verify(
        ~(fa2.data.ledger[token_id] == artist1.address))
    scenario.verify(
        ~(fa2.data.ledger[token_id] == marketplace.address))
    scenario.verify(fa2.data.ledger[token_id] == collector1.address)


@ sp.add_test(name="Test very cheap collect")
def test_very_cheap_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add marketplace contract as operator to be able to swap token
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap token in the marketplace contract for a very cheap price
    price = sp.mutez(2)

    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Collect the token
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))
    scenario.verify(fee_recipient.balance == sp.mutez(0))
    scenario.verify(artist1.balance == price)
    scenario.verify(marketplace.data.swaps[0].editions == 0)

    # Check that the token ledger information is correct
    scenario.verify(
        fa2.data.ledger[token_id] != artist1.address)
    scenario.verify(
        fa2.data.ledger[token_id] != marketplace.address)
    scenario.verify(
        fa2.data.ledger[token_id] == collector1.address)

    # Check the token ledger, but using views
    scenario.verify(fa2.get_balance(
        sp.record(owner=artist1.address, token_id=token_id)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=marketplace.address, token_id=token_id)) == 0)
    scenario.verify(fa2.get_balance(
        sp.record(owner=collector1.address, token_id=token_id)) == 1)


@ sp.add_test(name="Test update fee")
def test_update_fee():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    marketplace = testEnvironment["marketplace"]

    # Check the original fee
    scenario.verify(marketplace.data.fee == 25)
    scenario.verify(marketplace.get_fee() == 25)

    # Check that only the admin can update the fees
    new_fee = 100
    marketplace.update_fee(new_fee).run(valid=False, sender=artist1.address)
    marketplace.update_fee(new_fee).run(
        valid=False, sender=admin, amount=sp.tez(3))
    marketplace.update_fee(new_fee).run(sender=admin)

    # Check that the fee is updated
    scenario.verify(marketplace.data.fee == new_fee)
    scenario.verify(marketplace.get_fee() == new_fee)

    # Check that if fails if we try to set a fee that its too high
    new_fee = 500
    marketplace.update_fee(new_fee).run(valid=False, sender=admin)


@ sp.add_test(name="Test update fee recipient")
def test_update_fee_recipient():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    # Check the original fee recipient
    scenario.verify(marketplace.data.fee_recipient == fee_recipient.address)
    scenario.verify(marketplace.get_fee_recipient() == fee_recipient.address)

    # Check that only the admin can update the fee recipient
    new_fee_recipient = artist1.address
    marketplace.update_fee_recipient(new_fee_recipient).run(
        valid=False, sender=artist1.address)
    marketplace.update_fee_recipient(new_fee_recipient).run(
        valid=False, sender=admin, amount=sp.tez(3))
    marketplace.update_fee_recipient(new_fee_recipient).run(sender=admin)

    # Check that the fee recipient is updated
    scenario.verify(marketplace.data.fee_recipient == new_fee_recipient)
    scenario.verify(marketplace.get_fee_recipient() == new_fee_recipient)

    # Check that the fee recipient cannot update the fee recipient
    new_fee_recipient = artist2.address
    marketplace.update_fee_recipient(new_fee_recipient).run(
        valid=False, sender=artist1.address)


@ sp.add_test(name="Test transfer and accept administrator")
def test_transfer_and_accept_manager():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    marketplace = testEnvironment["marketplace"]

    # Check the original administrator
    scenario.verify(marketplace.data.administrator == admin.address)
    scenario.verify(marketplace.get_administrator() == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = artist1.address
    marketplace.transfer_administrator(new_administrator).run(
        valid=False, sender=artist1.address)
    marketplace.transfer_administrator(new_administrator).run(
        valid=False, sender=admin, amount=sp.tez(3))
    marketplace.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(
        marketplace.data.proposed_administrator.open_some() == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    marketplace.accept_administrator().run(valid=False, sender=admin)
    marketplace.accept_administrator().run(
        valid=False, sender=artist1.address, amount=sp.tez(3))
    marketplace.accept_administrator().run(sender=artist1.address)

    # Check that the administrator is updated
    scenario.verify(marketplace.data.administrator == new_administrator)
    scenario.verify(marketplace.get_administrator() == new_administrator)
    scenario.verify(~marketplace.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = artist2.address
    marketplace.transfer_administrator(
        new_administrator).run(valid=False, sender=admin)
    marketplace.transfer_administrator(
        new_administrator).run(sender=artist1.address)

    # Check that the proposed administrator is updated
    scenario.verify(
        marketplace.data.proposed_administrator.open_some() == new_administrator)


@ sp.add_test(name="Test set pause swaps")
def test_set_pause_swaps():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    price = sp.mutez(1000000)

    # Swap one token in the marketplace contract
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Swap second token in the marketplace contract
    token_id_2 = 134
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id_2))]).run(sender=artist1.address)
    marketplace.swap(
        token_id=token_id_2,
        price=price
    ).run(sender=artist1.address)

    # Pause the swaps and make sure only the admin can do it
    marketplace.set_pause_swaps(True).run(valid=False, sender=collector1)
    marketplace.set_pause_swaps(True).run(
        valid=False, sender=admin, amount=sp.tez(3))
    marketplace.set_pause_swaps(True).run(sender=admin)

    # Check that only the swaps are paused
    scenario.verify(marketplace.data.swaps_paused)
    scenario.verify(~marketplace.data.collects_paused)

    # Check that swapping is not allowed
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(valid=False, sender=artist1.address)

    # Check that collecting is still allowed
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that cancel swaps are still allowed
    marketplace.cancel_swap(token_id_2).run(sender=artist1.address)

    # Unpause the swaps again
    marketplace.set_pause_swaps(False).run(sender=admin)

    # Check that swapping and collecting is possible again
    token_id = 134

    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # can't cancel a fully collected swap (edition=0),
    # they should be automatically cancelled
    marketplace.cancel_swap(token_id).run(valid=False, sender=artist1.address)


@ sp.add_test(name="Test set pause collects")
def test_set_pause_collects():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap one token in the marketplace contract
    price = sp.mutez(1000000)
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Collect the OBJKT
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Pause the collects and make sure only the admin can do it
    marketplace.set_pause_collects(True).run(valid=False, sender=collector1)
    marketplace.set_pause_collects(True).run(
        valid=False, sender=admin, amount=sp.tez(3))
    marketplace.set_pause_collects(True).run(sender=admin)

    # Check that only the collects are paused
    scenario.verify(~marketplace.data.swaps_paused)
    scenario.verify(marketplace.data.collects_paused)

    # Check that collecting is not allowed
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=price)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 123
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Check that swapping is still allowed
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Check that cancel swaps are still allowed
    marketplace.cancel_swap(token_id).run(sender=artist1.address)

    # Unpause the collects again
    marketplace.set_pause_collects(False).run(sender=admin)

    # Check that swapping and collecting is possible again
    token_id = 207
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # can't cancel a fully collected swap (edition=0),
    # they should be automatically cancelled
    marketplace.cancel_swap(token_id).run(valid=False, sender=artist1.address)


@ sp.add_test(name="Test swap failure conditions")
def test_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    price = sp.mutez(1000000)

    # Trying to swap a token for which one doesn't have any editions must fail,
    # even for the admin
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(valid=False, sender=admin)

    # Successfully swap
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Check that the swap was added
    scenario.verify(marketplace.data.swaps.contains(token_id))

    scenario.verify(marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swap(
        token_id).editions == 1)

    scenario.verify(marketplace.data.counter == 1)

    # Second swap should now fail because all avalaible editions have beeen swapped
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(valid=False, sender=artist1.address)

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist2.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 300
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist2.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist2.address)

    # Successfully swap the second token
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist2.address)

    # Check that the swap was added
    scenario.verify(marketplace.data.swaps.contains(token_id))
    scenario.verify(marketplace.has_swap(token_id))
    scenario.verify(marketplace.get_swap(
        token_id).editions == 1)

    scenario.verify(marketplace.data.counter == 2)

    # Check that is not possible to swap the second token
    # because it was swapped before
    # and has only 1 edition
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(valid=False, sender=artist2.address)


@ sp.add_test(name="Test cancel swap failure conditions")
def test_cancel_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Successfully swap
    price = sp.mutez(10000)
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Check that the swap was added
    scenario.verify(marketplace.data.swaps.contains(token_id))
    scenario.verify(~marketplace.data.swaps.contains(1))
    scenario.verify(marketplace.data.counter == 1)

    # Check that cancelling a nonexistent swap fails
    marketplace.cancel_swap(1535).run(valid=False, sender=artist1.address)

    # Check that cancelling someone elses swap fails
    marketplace.cancel_swap(token_id).run(valid=False, sender=artist2.address)

    # Check that even the admin cannot cancel the swap
    marketplace.cancel_swap(token_id).run(valid=False, sender=admin)

    # Check that cancelling own swap works
    marketplace.cancel_swap(token_id).run(sender=artist1.address)

    # Check that the swaps big map has been updated
    # the map still holds a 0-edition swap
    scenario.verify(marketplace.data.swaps.contains(token_id))

    # but the views return correctly that the swap is not in effect
    scenario.verify(~marketplace.has_swap(token_id))
    sp.is_failing(~marketplace.get_swap(token_id))

    # Check that the swap counter is still incremented
    scenario.verify(marketplace.data.counter == 1)


@ sp.add_test(name="Test collect swap failure conditions")
def test_collect_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    #  Mint a token collection
    total = 256
    base = sp.utils.bytes_of_string(
        "ipfs://bafybeif7wihgyn4l5mny3m2zzga7rz7ous7szv3w4w54eijowmmcwogezi/")
    royalties = 100

    minter.mint(
        total=total,
        base=base,
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Successfully swap
    price = sp.mutez(100)
    marketplace.swap(
        token_id=token_id,
        price=price
    ).run(sender=artist1.address)

    # Check that trying to collect a nonexistent swap fails
    marketplace.collect(100).run(valid=False, sender=collector1, amount=price)

    # Check that trying to collect own swap fails
    marketplace.collect(token_id).run(
        valid=False, sender=artist1.address, amount=price)

    # Check that providing the wrong tez amount fails
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=price + sp.mutez(1))

    # Collect the token
    marketplace.collect(token_id).run(sender=collector1, amount=price)

    # Check that the swap entry still exists
    scenario.verify(marketplace.data.swaps.contains(token_id))

    # Check that there are no edition left for that swap
    scenario.verify(marketplace.data.swaps[token_id].editions == 0)
    scenario.verify(marketplace.data.counter == 1)

    # Check that trying to collect the swap fails
    marketplace.collect(token_id).run(
        valid=False, sender=collector1, amount=price)
