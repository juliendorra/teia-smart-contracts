
import smartpy as sp


class Marketplace(sp.Contract):
    """A basic marketplace contract for the extended FA2 token contract.

    """

    USER_ROYALTIES_TYPE = sp.TRecord(
        # The user address
        address=sp.TAddress,
        # The user royalties in per mille (100 is 10%)
        royalties=sp.TNat).layout(
            ("address", "royalties"))

    SWAP_TYPE = sp.TRecord(
        # The user that created the swap
        issuer=sp.TAddress,
        # The token id
        token_id=sp.TNat,
        # The number of swapped editions
        editions=sp.TNat,
        # The edition price in mutez
        price=sp.TMutez
    ).layout(
            ("issuer", ("token_id", ("editions", "price"))))

    PRICE_LIST = sp.TList(
        sp.TRecord(
            quantity=sp.TNat,
            price=sp.TMutez).layout(("quantity", "price"))
    )

    COLLECTION_SWAP_TYPE = sp.TRecord(
        # The user that created the swap
        issuer=sp.TAddress,
        # The token id
        collection_id=sp.TNat,
        first=sp.TNat,
        last=sp.TNat,
        # The edition price in mutez
        price_list=PRICE_LIST
    ).layout(
            ("issuer", ("collection_id", ("first", ("last", "price_list")))))

    def __init__(self, administrator, metadata, fa2, fee):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract administrador
            administrator=sp.TAddress,
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The FA2 token contract address
            fa2=sp.TAddress,
            # The marketplace fee taken for each collect operation in per mille
            fee=sp.TNat,
            # The address that will receive the marketplace fees
            fee_recipient=sp.TAddress,

            # The big map with the swaps information
            swaps=sp.TBigMap(sp.TNat, Marketplace.SWAP_TYPE),
            # The swaps counter
            counter=sp.TNat,

            # The big map with the collection swaps information
            collection_swaps=sp.TBigMap(
                sp.TNat, Marketplace.COLLECTION_SWAP_TYPE),
            # The collection swaps counter
            collection_swaps_counter=sp.TNat,

            # ID of highest (most recently minted) token swapped
            highest_token_swapped=sp.TNat,

            # The proposed new administrator address
            proposed_administrator=sp.TOption(sp.TAddress),
            # A flag that indicates if the marketplace swaps are paused
            swaps_paused=sp.TBool,
            # A flag that indicates if the marketplace collects are paused
            collects_paused=sp.TBool)
        )

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            fa2=fa2,
            fee=fee,
            fee_recipient=administrator,

            swaps=sp.big_map(),
            counter=0,

            collection_swaps=sp.big_map(),
            collection_swaps_counter=0,

            highest_token_swapped=0,

            proposed_administrator=sp.none,
            swaps_paused=False,
            collects_paused=False)

        # Build the TZIP-016 contract metadata
        # This is helpful to get the off-chain views code in json format
        contract_metadata = {
            "name": "Modified marketplace contract for collections",
            "description": "This contract allows for swapping whole collections of 1/1 tokens and single 1/1 tokens"
            "Based on Teia Community marketplace contract",
            "version": "v1.0.0",
            "authors": ["Teia Community <https://twitter.com/TeiaCommunity>"],
            "homepage": "https://teia.art",
            "source": {
                "tools": ["SmartPy 0.10.1"],
                "location": "https://github.com/teia-community/teia-smart-contracts/blob/main/python/marketplace/fa2.py"
            },
            "views": [
                self.get_administrator,
                self.has_swap,
                self.get_swap,
                self.get_swaps_counter,
                self.get_collection_swaps_counter,
                self.get_fee,
                self.get_fee_recipient,
            ]
        }

        self.init_metadata("contract_metadata", contract_metadata)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contract
        administrator.

        """
        sp.verify(sp.sender == self.data.administrator, message="MP_NOT_ADMIN")

    def check_no_tez_transfer(self):
        """Checks that no tez were transferred in the operation.

        """
        sp.verify(sp.amount == sp.tez(0), message="MP_TEZ_TRANSFER")

    @sp.entry_point
    def swap(self, params):
        """Swaps one edition of a token for a fixed price.

        Note that for this operation to work, the marketplace contract should
        be added before as an operator of the token by the swap issuer.
        It's recommended to remove the marketplace operator rights after
        calling this entry point.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            token_id=sp.TNat,
            price=sp.TMutez
        ).layout(("token_id", "price"))
        )

        # Check that swaps are not paused
        sp.verify(~self.data.swaps_paused, message="MP_SWAPS_PAUSED")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that royalties + fee does not exceed 100%
        royalties = sp.local("royalties",
                             self.get_token_royalties(params.token_id))

        total = sp.local("total",
                         self.data.fee +
                         royalties.value.minter.royalties +
                         royalties.value.creator.royalties)

        sp.verify(total.value <= 1000, message="MP_TOO_HIGH_ROYALTIES")

        single_edition = 1

        # Transfer 1 edition to the marketplace account
        self.fa2_transfer(
            fa2=self.data.fa2,
            from_=sp.sender,
            to_=sp.self_address,
            token_id=params.token_id,
            token_amount=single_edition)

        # Update the swaps bigmap with the new swap information
        # as we are swapping tokens that are all 1/1,
        # we take the shortcut swap_id = token_id
        self.data.swaps[params.token_id] = sp.record(
            issuer=sp.sender,
            token_id=params.token_id,
            editions=single_edition,
            price=params.price)

        # Increase the swaps counter
        self.data.counter += 1

        # Set the highest swapped token
        with sp.if_(params.token_id > self.data.highest_token_swapped):
            self.data.highest_token_swapped = params.token_id

    @sp.entry_point
    def swap_collection(self, params):
        """Swaps a whole new collection at once, with automatically assigned prices.

        Note that for this operation to work, the marketplace contract MUST be added before as an operator of the collection by the swap issuer.
        It's recommended to remove the marketplace operator rights after
        calling this entry point.

        For the whole collection to be transfered, the collection should also be brand new,
        still in full lazy ledger mode. If one or more tokens have already been transfered, the collection transfer will fail

        [8,  3000000], [26, 5000000], [30, 7000000], [
            128,  10000000], [64, 15000000]

        sp.tez(1)  =    sp.mutez(1000000)

        If more tokens than available are specified in the price list, swap will fail

        ==> it would be better to just check and error if the total > tokens in collection,
        but it means asking the FA2 contract for infos

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            collection_id=sp.TNat,
            price_list=sp.TList(
                sp.TRecord(
                    quantity=sp.TNat,
                    price=sp.TMutez).layout(("quantity", "price"))
            )
        ).layout(("collection_id", "price_list"))
        )

        # Check that swaps are not paused
        sp.verify(~self.data.swaps_paused, message="MP_SWAPS_PAUSED")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that royalties + fee does not exceed 100%
        royalties = sp.local("royalties",
                             self.get_collection_royalties(params.collection_id))

        total = sp.local("total",
                         self.data.fee +
                         royalties.value.minter.royalties +
                         royalties.value.creator.royalties)

        sp.verify(total.value <= 1000, message="MP_TOO_HIGH_ROYALTIES")

        first_last_tokens = sp.local(
            "first_last_tokens", self.get_collection_first_last_tokens(params.collection_id))

        # first = 0
        # last = 255
        # token_quantity = 255-(0-1) = 256

        token_quantity = sp.local("token_quantity",
                                  sp.as_nat(
                                      sp.to_int(first_last_tokens.value.last) -
                                      (sp.to_int(first_last_tokens.value.first) - 1)
                                  )
                                  )

        # sp.trace(token_quantity.value)

        token_priced_quantity = sp.local("token_priced_quantity", sp.nat(0))

        with sp.for_("price_entry", params.price_list) as price_entry:
            # sp.trace(price_entry.quantity)
            token_priced_quantity.value = token_priced_quantity.value + price_entry.quantity

        # sp.trace(token_priced_quantity.value)

        sp.verify(token_priced_quantity.value == token_quantity.value,
                  message="MP_PRICELIST_NOT_SUMMING_TO_TOKEN_QUANTITY")

        # Transfer the collection to the marketplace address
        # This gives the marketplace full control
        # over individual tokens in the collection
        self.fa2_collection_transfer(
            fa2=self.data.fa2,
            from_=sp.sender,
            to_=sp.self_address,
            collection_id=params.collection_id)

        # Update the collection swaps bigmap with the new swap information
        self.data.collection_swaps[params.collection_id] = sp.record(
            issuer=sp.sender,
            collection_id=params.collection_id,
            first=first_last_tokens.value.first,
            last=first_last_tokens.value.last,
            price_list=params.price_list)

        # Increase the swaps counter
        self.data.collection_swaps_counter += 1

        # # Set the highest swapped token
        with sp.if_(first_last_tokens.value.last > self.data.highest_token_swapped):
            self.data.highest_token_swapped = first_last_tokens.value.last

    @sp.entry_point
    def collect(self, token_id):
        """Collects one edition of a token that has already been swapped.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Check that collects are not paused
        sp.verify(~self.data.collects_paused, message="MP_COLLECTS_PAUSED")

        # Check that the swap id is present in the swaps big map
        with sp.if_(self.data.swaps.contains(token_id)):

            # Check that the collector is not the creator of the swap
            swap = sp.local("swap", self.data.swaps[token_id])

            sp.verify(sp.sender != swap.value.issuer,
                      message="MP_IS_SWAP_ISSUER")

            # Check that there is at least one edition available to collect
            sp.verify(swap.value.editions > 0, message="MP_SWAP_COLLECTED")

            # Check that the provided mutez amount is exactly the edition price
            sp.verify(sp.amount == swap.value.price,
                      message="MP_WRONG_TEZ_AMOUNT")

            # Handle tez tranfers if the edition price is not zero
            with sp.if_(sp.amount != sp.mutez(0)):
                # Get the royalties information from the FA2 token contract
                royalties = sp.local(
                    "royalties", self.get_token_royalties(token_id))

                # Send the royalties to the token minter
                minter_royalties_amount = sp.local(
                    "minter_royalties_amount", sp.split_tokens(
                        sp.amount, royalties.value.minter.royalties, 1000))

                with sp.if_(minter_royalties_amount.value > sp.mutez(0)):
                    sp.send(royalties.value.minter.address,
                            minter_royalties_amount.value)

                # Send the royalties to the token creator
                creator_royalties_amount = sp.local(
                    "creator_royalties_amount", sp.split_tokens(
                        sp.amount, royalties.value.creator.royalties, 1000))

                with sp.if_(creator_royalties_amount.value > sp.mutez(0)):
                    sp.send(royalties.value.creator.address,
                            creator_royalties_amount.value)

                # Send the management fees
                fee_amount = sp.local(
                    "fee_amount", sp.split_tokens(sp.amount, self.data.fee, 1000))

                with sp.if_(fee_amount.value > sp.mutez(0)):
                    sp.send(self.data.fee_recipient, fee_amount.value)

                # Send what is left to the swap issuer
                sp.send(swap.value.issuer,
                        sp.amount -
                        minter_royalties_amount.value -
                        creator_royalties_amount.value -
                        fee_amount.value)

            # Transfer the token edition to the collector
            self.fa2_transfer(
                fa2=self.data.fa2,
                from_=sp.self_address,
                to_=sp.sender,
                token_id=token_id,
                token_amount=1)

            # Update the number of editions available in the swaps big map
            # It will set it to zero, as in this contract,
            # all swaps are fixed at 1 edition
            # to account for our own FA2 contract
            self.data.swaps[token_id].editions = sp.as_nat(
                swap.value.editions - 1)

        # If there's no swap for a single token,
        # check if the whole collection of the token is swapped
        with sp.else_():
            self.try_collect_inside_collection(token_id)

    def try_collect_inside_collection(self, token_id):

        collection_id = sp.local(
            "collection_id", self.get_token_collection_id(token_id))

        # Check that the collection has been swapped
        sp.verify(self.data.collection_swaps.contains(
            collection_id.value), message="MP_WRONG_SWAP_ID")

        # Check that the token is not already transfered out of the
        # marketplace ie. that the owner is still the marketplace address

        # Check that the collector is not the creator of the swap
        swap = sp.local(
            "swap", self.data.collection_swaps[collection_id.value])

        sp.verify(sp.sender != swap.value.issuer,
                  message="MP_IS_SWAP_ISSUER")

        # Check that the provided mutez amount is exactly the edition price

        price = self.calculate_token_price_in_collection_swap(
            token_id, swap)

        sp.verify(sp.amount == price, message="MP_WRONG_TEZ_AMOUNT")

        # Handle tez tranfers if the edition price is not zero
        with sp.if_(sp.amount != sp.mutez(0)):
            # Get the royalties information from the FA2 token contract
            royalties = sp.local(
                "royalties", self.get_token_royalties(token_id))

            # Send the royalties to the token minter
            minter_royalties_amount = sp.local(
                "minter_royalties_amount", sp.split_tokens(
                    sp.amount, royalties.value.minter.royalties, 1000))

            with sp.if_(minter_royalties_amount.value > sp.mutez(0)):
                sp.send(royalties.value.minter.address,
                        minter_royalties_amount.value)

            # Send the royalties to the token creator
            creator_royalties_amount = sp.local(
                "creator_royalties_amount", sp.split_tokens(
                    sp.amount, royalties.value.creator.royalties, 1000))

            with sp.if_(creator_royalties_amount.value > sp.mutez(0)):
                sp.send(royalties.value.creator.address,
                        creator_royalties_amount.value)

            # Send the management fees
            fee_amount = sp.local(
                "fee_amount", sp.split_tokens(sp.amount, self.data.fee, 1000))

            with sp.if_(fee_amount.value > sp.mutez(0)):
                sp.send(self.data.fee_recipient, fee_amount.value)

            # Send what is left to the swap issuer
            sp.send(swap.value.issuer,
                    sp.amount -
                    minter_royalties_amount.value -
                    creator_royalties_amount.value -
                    fee_amount.value)

        # Transfer the token edition to the collector
        self.fa2_transfer(
            fa2=self.data.fa2,
            from_=sp.self_address,
            to_=sp.sender,
            token_id=token_id,
            token_amount=1)

        # Creates an empty swap entry as if we just swapped a single token out.
        # That effectively marks the token as not swappable in the collection
        # The whole collection is swapped, but this token has been transfered
        # to another owner than the fresh collection owner, so we should never
        # be able to rely on the collection swap for this token again

        # Update the swaps bigmap with the 0 edition swap
        # as we are swapping tokens that are all 1/1,
        # we take the shortcut swap_id = token_id
        self.data.swaps[token_id] = sp.record(
            issuer=sp.sender,
            token_id=token_id,
            editions=0,
            price=sp.mutez(0))

    @sp.entry_point
    def cancel_swap(self, token_id):
        """Cancels an existing swap.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

       # Check that the swap id is present in the swaps big map
        with sp.if_(self.data.swaps.contains(token_id)):

            # Check that the swap id is present in the swaps big map
            # sp.verify(self.data.swaps.contains(token_id), message="MP_WRONG_SWAP_ID")

            # Check that the swap issuer is cancelling the swap
            swap = sp.local("swap", self.data.swaps[token_id])
            sp.verify(sp.sender == swap.value.issuer,
                      message="MP_NOT_SWAP_ISSUER")

            # Check that there is at least one swapped edition
            sp.verify(swap.value.editions > 0, message="MP_SWAP_COLLECTED")

            # Transfer the remaining token editions back to the owner
            self.fa2_transfer(
                fa2=self.data.fa2,
                from_=sp.self_address,
                to_=sp.sender,
                token_id=swap.value.token_id,
                token_amount=swap.value.editions)

            # Delete the swap entry in the the swaps big map
            # we don't delete swaps
            # As we we use swaps to keep an history of single tokens
            # transfered out of a collection swap by the marketplace
            # del self.data.swaps[token_id]

            # Update the swaps bigmap with an empty swap
            self.data.swaps[token_id] = sp.record(
                issuer=swap.value.issuer,
                token_id=swap.value.token_id,
                editions=0,
                price=sp.mutez(0))

        # If there's no swap for a single token,
        # check if the whole collection of the token is swapped
        with sp.else_():
            collection_id = sp.local(
                "collection_id", self.get_token_collection_id(token_id))

            # Check that the collection has been swapped
            sp.verify(self.data.collection_swaps.contains(
                collection_id.value), message="MP_WRONG_SWAP_ID")

            # Check that the swap issuer is cancelling the swap
            swap = sp.local(
                "swap", self.data.collection_swaps[collection_id.value])
            sp.verify(sp.sender == swap.value.issuer,
                      message="MP_NOT_SWAP_ISSUER")

            # Transfer the token back to the owner
            self.fa2_transfer(
                fa2=self.data.fa2,
                from_=sp.self_address,
                to_=sp.sender,
                token_id=token_id,
                token_amount=1)

            # Creates an empty swap entry for the token
            # That effectively marks the token as not swapped
            # and outside the collection swap
            # The whole collection is swapped,
            # but this token is now treated separatedly

            # Update the swaps bigmap with the 0 edition swap
            # as we are swapping tokens that are all 1/1,
            # we take the shortcut swap_id = token_id
            self.data.swaps[token_id] = sp.record(
                issuer=sp.sender,
                token_id=token_id,
                editions=0,
                price=sp.mutez(0))

    @sp.entry_point
    def update_fee(self, new_fee):
        """Updates the marketplace management fees.

        """
        # Define the input parameter data type
        sp.set_type(new_fee, sp.TNat)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the new fee is not larger than 25%
        sp.verify(new_fee <= 250, message="MP_WRONG_FEES")

        # Set the new management fee
        self.data.fee = new_fee

    @sp.entry_point
    def update_fee_recipient(self, new_fee_recipient):
        """Updates the marketplace management fee recipient address.

        """
        # Define the input parameter data type
        sp.set_type(new_fee_recipient, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new management fee recipient address
        self.data.fee_recipient = new_fee_recipient

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contract administrator to another address.

        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contract administrator
        responsabilities.

        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(),
                  message="MP_NO_NEW_ADMIN")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(),
                  message="MP_NOT_PROPOSED_ADMIN")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.entry_point
    def set_pause_swaps(self, pause):
        """Pause or not the swaps.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the swaps
        self.data.swaps_paused = pause

    @sp.entry_point
    def set_pause_collects(self, pause):
        """Pause or not the collects.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the collects
        self.data.collects_paused = pause

    @ sp.onchain_view()
    def get_administrator(self):
        """Returns the marketplace administrator address.

        """
        sp.result(self.data.administrator)

    @sp.onchain_view()
    def has_swap(self, swap_id):
        """Check if a given swap id is present in the swaps big map.

        Swap with 0 editions are considered non existing

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that the swap id is present in the swaps big map
        with sp.if_(self.data.swaps.contains(swap_id)):
            # Return True if the swap id is present in the swaps big map
            # and is holding 1 edition
            # Return False is the swap was created but is now zero
            # (In that case we don't want to check for a collection swap)
            sp.result(self.data.swaps[swap_id].editions > 0)

        # If there's no swap at all, 0 or 1 edition, for a single token,
        # We check if the whole collection of the token is swapped
        with sp.else_():
            collection_id = self.get_token_collection_id(swap_id)
            sp.result(
                self.data.collection_swaps.contains(collection_id))

    @ sp.onchain_view()
    def get_swap(self, swap_id):
        """Returns the complete information from a given swap id.

        Swap with 0 editions are considered non existing and returns error

        It also return error if collection is swapped,
        but token was already traded out
        as the collect entry point creates a 0-edition swap in this case

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # create a local variable containing a base, 0-edition swap
        token_swap = sp.local("token_swap",
                              sp.record(
                                  issuer=sp.address(
                                      "tz1ahsDNFzukj51hVpW626qH7Ug9HeUVQDNG"),
                                  token_id=sp.nat(0),
                                  editions=sp.nat(0),
                                  price=sp.mutez(0)
                              )
                              )

        # Check that the swap id is present in the swaps big map
        with sp.if_(self.data.swaps.contains(swap_id)):
            token_swap.value = self.data.swaps[swap_id]

        # if there's no swap at all for it as single token,
        # check if the whole collection of the token is swapped
        with sp.else_():

            collection_id = self.get_token_collection_id(swap_id)

            # collection_swap record:
            # issuer=sp.sender,
            # collection_id=params.collection_id,
            # first=first_last_tokens.first,
            # last=first_last_tokens.last,
            # price_list=params.price_list

            with sp.if_(self.data.collection_swaps.contains(collection_id)):
                collection_swap = sp.local(
                    "collection_swap", self.data.collection_swaps[collection_id])

                token_swap.value.issuer = collection_swap.value.issuer
                token_swap.value.token_id = swap_id
                token_swap.value.editions = 1
                token_swap.value.price = self.calculate_token_price_in_collection_swap(
                    swap_id, collection_swap)

        # No Swap, an empty Swap or no collection swap were found
        sp.verify(token_swap.value.editions > 0, "MP_WRONG_SWAP_ID")

        # Return the swap information only if it is holding 1 edition
        sp.result(token_swap.value)

    @ sp.onchain_view()
    def get_swaps_counter(self):
        """Returns the swaps counter.

        """
        sp.result(self.data.counter)

    @ sp.onchain_view()
    def get_collection_swaps_counter(self):
        """Returns the swaps counter.

        """
        sp.result(self.data.collection_swaps_counter)

    @ sp.onchain_view()
    def get_fee(self):
        """Returns the marketplace fee.

        """
        sp.result(self.data.fee)

    @ sp.onchain_view()
    def get_fee_recipient(self):
        """Returns the marketplace fee recipient address.

        """
        sp.result(self.data.fee_recipient)

    def fa2_transfer(self, fa2, from_, to_, token_id, token_amount):
        """Transfers a number of editions of a FA2 token between two addresses.

        """
        # Get a handle to the FA2 token transfer entry point
        c = sp.contract(
            t=sp.TList(sp.TRecord(
                from_=sp.TAddress,
                txs=sp.TList(sp.TRecord(
                    to_=sp.TAddress,
                    token_id=sp.TNat,
                    amount=sp.TNat).layout(("to_", ("token_id", "amount")))))),
            address=fa2,
            entry_point="transfer").open_some()

        # Transfer the FA2 token editions to the new address
        sp.transfer(
            arg=sp.list([sp.record(
                from_=from_,
                txs=sp.list([sp.record(
                    to_=to_,
                    token_id=token_id,
                    amount=token_amount)]))]),
            amount=sp.mutez(0),
            destination=c)

    def fa2_collection_transfer(self, fa2, from_, to_, collection_id):
        """Transfers a lazy ledger collection between two addresses.

        """
        # Get a handle to the collection transfer entry point
        c = sp.contract(
            t=sp.TRecord(
                from_=sp.TAddress,
                to_=sp.TAddress,
                collection_id=sp.TNat).layout(
                ("from_", ("to_", "collection_id"))
            ),
            address=fa2,
            entry_point="transfer_collection").open_some()

        # Transfer the collection to the new address
        sp.transfer(
            arg=sp.record(
                from_=from_,
                to_=to_,
                collection_id=collection_id),
            amount=sp.mutez(0),
            destination=c)

    def get_token_royalties(self, token_id):
        """Gets the token royalties information calling the FA2 contract
        on-chain view.

        """
        return sp.view(
            name="token_royalties",
            address=self.data.fa2,
            param=token_id,
            t=sp.TRecord(
                minter=Marketplace.USER_ROYALTIES_TYPE,
                creator=Marketplace.USER_ROYALTIES_TYPE).layout(
                ("minter", "creator"))
        ).open_some()

    def get_collection_royalties(self, collection_id):
        """Gets the collection royalties information calling the FA2 contract
        on-chain view.

        """
        return sp.view(
            name="collection_royalties",
            address=self.data.fa2,
            param=collection_id,
            t=sp.TRecord(
                minter=Marketplace.USER_ROYALTIES_TYPE,
                creator=Marketplace.USER_ROYALTIES_TYPE).layout(
                ("minter", "creator"))
        ).open_some()

    def get_collection_first_last_tokens(self, collection_id):
        """Gets the first and last token ids for a collection 
        calling the FA2 contract on-chain view.

        """

        return sp.view(
            name="collection_first_last_tokens",
            address=self.data.fa2,
            param=collection_id,
            t=sp.TRecord(
                first=sp.TNat,
                last=sp.TNat).layout(
                ("first", "last"))
        ).open_some()

    def get_token_collection_id(self, token_id):
        """Gets collection id for a token
        calling the FA2 contract on-chain view.

        """

        return sp.view(
            name="get_token_collection_id",
            address=self.data.fa2,
            param=token_id,
            t=sp.TNat
        ).open_some()

    def calculate_token_price_in_collection_swap(self, token_id, swap):
        # Calculate the token price in a collection swap
        # exemple : 345 - 256 = 89
        # token_index_from_0 = token_id - swap.value.first
        #
        # iterate on price list
        # add quantity to token_quantity_index
        # if token_quantity_index >= token_index_from_0
        # then the price is the price of this token

        token_index_from_0 = sp.local(
            "token_index_from_0", sp.as_nat(token_id - swap.value.first))

        token_quantity_amount = sp.local("token_quantity_index", 0)
        price = sp.local("price", sp.mutez(0))
        price_reached = sp.local("price_reached", False)

        with sp.for_("price_entry", swap.value.price_list) as price_entry:

            token_quantity_amount.value = token_quantity_amount.value + price_entry.quantity
            # token_index_from_0 is 0-indexed
            # but quantity is 1-indexed
            # that's why we use stricly superior (and not >=)
            with sp.if_(
                    (token_quantity_amount.value > token_index_from_0.value)
                    & ~price_reached.value):
                price.value = price_entry.price
                price_reached.value = True

        return price.value


sp.add_compilation_target("marketplace", Marketplace(
    administrator=sp.address("tz1ahsDNFzukj51hVpW626qH7Ug9HeUVQDNG"),
    metadata=sp.utils.metadata_of_url(
        "ipfs://bafkreifzjjdvpyiewz6cnj66v5lahnar2vppj2jfjejtgnwybh3u23fk6e"),
    fa2=sp.address("KT1HKXQJo6Jt3Bt13h1fTEqCNov4N4X3w1t8"),
    fee=sp.nat(25)))
