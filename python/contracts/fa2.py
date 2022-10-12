import smartpy as sp


class FA2(sp.Contract):
    """This contract tries to simplify and extend the FA2 contract template
    example in smartpy.io v0.9.1.

    The FA2 template was originally developed by Seb Mondet:
    https://gitlab.com/smondet/fa2-smartpy

    The contract follows the FA2 standard specification:
    https://gitlab.com/tezos/tzip/-/blob/master/proposals/tzip-12/tzip-12.md

    """

    USER_ROYALTIES_TYPE = sp.TRecord(
        # The user address
        address=sp.TAddress,
        # The user royalties in per mille (100 is 10%)
        royalties=sp.TNat).layout(
            ("address", "royalties"))

    TOKEN_ROYALTIES_VALUE_TYPE = sp.TRecord(
        # The token original minter
        minter=USER_ROYALTIES_TYPE,
        # The token creator (it could be a single creator or a collaboration)
        creator=USER_ROYALTIES_TYPE).layout(
            ("minter", "creator"))

    OPERATOR_KEY_TYPE = sp.TRecord(
        # The owner of the token editions
        owner=sp.TAddress,
        # The operator allowed by the owner to transfer their token editions
        operator=sp.TAddress,
        # The token id
        token_id=sp.TNat).layout(
            ("owner", ("operator", "token_id")))

    COLLECTION_OPERATOR_KEY_TYPE = sp.TRecord(
        # The owner of collection
        owner=sp.TAddress,
        # The operator allowed by the owner to transfer their collection
        operator=sp.TAddress,
        # The collection id
        collection_id=sp.TNat).layout(
        ("owner", ("operator", "collection_id")))

    def __init__(self, administrator, metadata):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract administrator
            administrator=sp.TAddress,
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The ledger big map where the tokens owners are listed
            ledger=sp.TBigMap(sp.TNat, sp.TAddress),
            # The big map where the tokens initial creators are listed when minted
            collection_ledger=sp.TBigMap(sp.TNat, sp.TAddress),

            # Collection management: storing the base url only once for a whole collection
            # The big map with the tokens collection IDs
            token_collection=sp.TBigMap(
                sp.TNat, sp.TNat),
            # The big map with the collection base url
            collection_base_url=sp.TBigMap(
                sp.TNat, sp.TBytes),
            # Counter that tracks the total number of collections
            collection_counter=sp.TNat,
            # The big map with the first token_id of each collection
            collection_start_id=sp.TBigMap(sp.TNat, sp.TNat),
            # The big map tracking the state of collections
            collection_not_fresh=sp.TBigMap(sp.TNat, sp.TUnit),

            # The big map with the collection royalties for the minter and creators
            collection_royalties=sp.TBigMap(
                sp.TNat, FA2.TOKEN_ROYALTIES_VALUE_TYPE),
            # The big map with the collecrion operators
            collection_operators=sp.TBigMap(
                FA2.COLLECTION_OPERATOR_KEY_TYPE, sp.TUnit),

            # The big map with the tokens operators
            operators=sp.TBigMap(FA2.OPERATOR_KEY_TYPE, sp.TUnit),
            # The proposed new administrator address
            proposed_administrator=sp.TOption(sp.TAddress),
            # A counter that tracks the total number of tokens minted so far
            counter=sp.TNat,

            # A static map to convert from nat to their bytes representation
            token_name_map=sp.TMap(sp.TNat, sp.TBytes),

        ))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            ledger=sp.big_map(),
            collection_ledger=sp.big_map(),
            token_collection=sp.big_map(),
            collection_base_url=sp.big_map(),
            collection_start_id=sp.big_map(),
            collection_not_fresh=sp.big_map(),
            collection_royalties=sp.big_map(),
            collection_operators=sp.big_map(),
            operators=sp.big_map(),
            proposed_administrator=sp.none,
            counter=0,
            collection_counter=0,
            token_name_map={
                0: sp.bytes("0x30"),
                1: sp.bytes("0x31"),
                2: sp.bytes("0x32"),
                3: sp.bytes("0x33"),
                4: sp.bytes("0x34"),
                5: sp.bytes("0x35"),
                6: sp.bytes("0x36"),
                7: sp.bytes("0x37"),
                8: sp.bytes("0x38"),
                9: sp.bytes("0x39"),
                10: sp.bytes("0x3130"),
                11: sp.bytes("0x3131"),
                12: sp.bytes("0x3132"),
                13: sp.bytes("0x3133"),
                14: sp.bytes("0x3134"),
                15: sp.bytes("0x3135"),
                16: sp.bytes("0x3136"),
                17: sp.bytes("0x3137"),
                18: sp.bytes("0x3138"),
                19: sp.bytes("0x3139"),
                20: sp.bytes("0x3230"),
                21: sp.bytes("0x3231"),
                22: sp.bytes("0x3232"),
                23: sp.bytes("0x3233"),
                24: sp.bytes("0x3234"),
                25: sp.bytes("0x3235"),
                26: sp.bytes("0x3236"),
                27: sp.bytes("0x3237"),
                28: sp.bytes("0x3238"),
                29: sp.bytes("0x3239"),
                30: sp.bytes("0x3330"),
                31: sp.bytes("0x3331"),
                32: sp.bytes("0x3332"),
                33: sp.bytes("0x3333"),
                34: sp.bytes("0x3334"),
                35: sp.bytes("0x3335"),
                36: sp.bytes("0x3336"),
                37: sp.bytes("0x3337"),
                38: sp.bytes("0x3338"),
                39: sp.bytes("0x3339"),
                40: sp.bytes("0x3430"),
                41: sp.bytes("0x3431"),
                42: sp.bytes("0x3432"),
                43: sp.bytes("0x3433"),
                44: sp.bytes("0x3434"),
                45: sp.bytes("0x3435"),
                46: sp.bytes("0x3436"),
                47: sp.bytes("0x3437"),
                48: sp.bytes("0x3438"),
                49: sp.bytes("0x3439"),
                50: sp.bytes("0x3530"),
                51: sp.bytes("0x3531"),
                52: sp.bytes("0x3532"),
                53: sp.bytes("0x3533"),
                54: sp.bytes("0x3534"),
                55: sp.bytes("0x3535"),
                56: sp.bytes("0x3536"),
                57: sp.bytes("0x3537"),
                58: sp.bytes("0x3538"),
                59: sp.bytes("0x3539"),
                60: sp.bytes("0x3630"),
                61: sp.bytes("0x3631"),
                62: sp.bytes("0x3632"),
                63: sp.bytes("0x3633"),
                64: sp.bytes("0x3634"),
                65: sp.bytes("0x3635"),
                66: sp.bytes("0x3636"),
                67: sp.bytes("0x3637"),
                68: sp.bytes("0x3638"),
                69: sp.bytes("0x3639"),
                70: sp.bytes("0x3730"),
                71: sp.bytes("0x3731"),
                72: sp.bytes("0x3732"),
                73: sp.bytes("0x3733"),
                74: sp.bytes("0x3734"),
                75: sp.bytes("0x3735"),
                76: sp.bytes("0x3736"),
                77: sp.bytes("0x3737"),
                78: sp.bytes("0x3738"),
                79: sp.bytes("0x3739"),
                80: sp.bytes("0x3830"),
                81: sp.bytes("0x3831"),
                82: sp.bytes("0x3832"),
                83: sp.bytes("0x3833"),
                84: sp.bytes("0x3834"),
                85: sp.bytes("0x3835"),
                86: sp.bytes("0x3836"),
                87: sp.bytes("0x3837"),
                88: sp.bytes("0x3838"),
                89: sp.bytes("0x3839"),
                90: sp.bytes("0x3930"),
                91: sp.bytes("0x3931"),
                92: sp.bytes("0x3932"),
                93: sp.bytes("0x3933"),
                94: sp.bytes("0x3934"),
                95: sp.bytes("0x3935"),
                96: sp.bytes("0x3936"),
                97: sp.bytes("0x3937"),
                98: sp.bytes("0x3938"),
                99: sp.bytes("0x3939"),
                100: sp.bytes("0x313030"),
                101: sp.bytes("0x313031"),
                102: sp.bytes("0x313032"),
                103: sp.bytes("0x313033"),
                104: sp.bytes("0x313034"),
                105: sp.bytes("0x313035"),
                106: sp.bytes("0x313036"),
                107: sp.bytes("0x313037"),
                108: sp.bytes("0x313038"),
                109: sp.bytes("0x313039"),
                110: sp.bytes("0x313130"),
                111: sp.bytes("0x313131"),
                112: sp.bytes("0x313132"),
                113: sp.bytes("0x313133"),
                114: sp.bytes("0x313134"),
                115: sp.bytes("0x313135"),
                116: sp.bytes("0x313136"),
                117: sp.bytes("0x313137"),
                118: sp.bytes("0x313138"),
                119: sp.bytes("0x313139"),
                120: sp.bytes("0x313230"),
                121: sp.bytes("0x313231"),
                122: sp.bytes("0x313232"),
                123: sp.bytes("0x313233"),
                124: sp.bytes("0x313234"),
                125: sp.bytes("0x313235"),
                126: sp.bytes("0x313236"),
                127: sp.bytes("0x313237"),
                128: sp.bytes("0x313238"),
                129: sp.bytes("0x313239"),
                130: sp.bytes("0x313330"),
                131: sp.bytes("0x313331"),
                132: sp.bytes("0x313332"),
                133: sp.bytes("0x313333"),
                134: sp.bytes("0x313334"),
                135: sp.bytes("0x313335"),
                136: sp.bytes("0x313336"),
                137: sp.bytes("0x313337"),
                138: sp.bytes("0x313338"),
                139: sp.bytes("0x313339"),
                140: sp.bytes("0x313430"),
                141: sp.bytes("0x313431"),
                142: sp.bytes("0x313432"),
                143: sp.bytes("0x313433"),
                144: sp.bytes("0x313434"),
                145: sp.bytes("0x313435"),
                146: sp.bytes("0x313436"),
                147: sp.bytes("0x313437"),
                148: sp.bytes("0x313438"),
                149: sp.bytes("0x313439"),
                150: sp.bytes("0x313530"),
                151: sp.bytes("0x313531"),
                152: sp.bytes("0x313532"),
                153: sp.bytes("0x313533"),
                154: sp.bytes("0x313534"),
                155: sp.bytes("0x313535"),
                156: sp.bytes("0x313536"),
                157: sp.bytes("0x313537"),
                158: sp.bytes("0x313538"),
                159: sp.bytes("0x313539"),
                160: sp.bytes("0x313630"),
                161: sp.bytes("0x313631"),
                162: sp.bytes("0x313632"),
                163: sp.bytes("0x313633"),
                164: sp.bytes("0x313634"),
                165: sp.bytes("0x313635"),
                166: sp.bytes("0x313636"),
                167: sp.bytes("0x313637"),
                168: sp.bytes("0x313638"),
                169: sp.bytes("0x313639"),
                170: sp.bytes("0x313730"),
                171: sp.bytes("0x313731"),
                172: sp.bytes("0x313732"),
                173: sp.bytes("0x313733"),
                174: sp.bytes("0x313734"),
                175: sp.bytes("0x313735"),
                176: sp.bytes("0x313736"),
                177: sp.bytes("0x313737"),
                178: sp.bytes("0x313738"),
                179: sp.bytes("0x313739"),
                180: sp.bytes("0x313830"),
                181: sp.bytes("0x313831"),
                182: sp.bytes("0x313832"),
                183: sp.bytes("0x313833"),
                184: sp.bytes("0x313834"),
                185: sp.bytes("0x313835"),
                186: sp.bytes("0x313836"),
                187: sp.bytes("0x313837"),
                188: sp.bytes("0x313838"),
                189: sp.bytes("0x313839"),
                190: sp.bytes("0x313930"),
                191: sp.bytes("0x313931"),
                192: sp.bytes("0x313932"),
                193: sp.bytes("0x313933"),
                194: sp.bytes("0x313934"),
                195: sp.bytes("0x313935"),
                196: sp.bytes("0x313936"),
                197: sp.bytes("0x313937"),
                198: sp.bytes("0x313938"),
                199: sp.bytes("0x313939"),
                200: sp.bytes("0x323030"),
                201: sp.bytes("0x323031"),
                202: sp.bytes("0x323032"),
                203: sp.bytes("0x323033"),
                204: sp.bytes("0x323034"),
                205: sp.bytes("0x323035"),
                206: sp.bytes("0x323036"),
                207: sp.bytes("0x323037"),
                208: sp.bytes("0x323038"),
                209: sp.bytes("0x323039"),
                210: sp.bytes("0x323130"),
                211: sp.bytes("0x323131"),
                212: sp.bytes("0x323132"),
                213: sp.bytes("0x323133"),
                214: sp.bytes("0x323134"),
                215: sp.bytes("0x323135"),
                216: sp.bytes("0x323136"),
                217: sp.bytes("0x323137"),
                218: sp.bytes("0x323138"),
                219: sp.bytes("0x323139"),
                220: sp.bytes("0x323230"),
                221: sp.bytes("0x323231"),
                222: sp.bytes("0x323232"),
                223: sp.bytes("0x323233"),
                224: sp.bytes("0x323234"),
                225: sp.bytes("0x323235"),
                226: sp.bytes("0x323236"),
                227: sp.bytes("0x323237"),
                228: sp.bytes("0x323238"),
                229: sp.bytes("0x323239"),
                230: sp.bytes("0x323330"),
                231: sp.bytes("0x323331"),
                232: sp.bytes("0x323332"),
                233: sp.bytes("0x323333"),
                234: sp.bytes("0x323334"),
                235: sp.bytes("0x323335"),
                236: sp.bytes("0x323336"),
                237: sp.bytes("0x323337"),
                238: sp.bytes("0x323338"),
                239: sp.bytes("0x323339"),
                240: sp.bytes("0x323430"),
                241: sp.bytes("0x323431"),
                242: sp.bytes("0x323432"),
                243: sp.bytes("0x323433"),
                244: sp.bytes("0x323434"),
                245: sp.bytes("0x323435"),
                246: sp.bytes("0x323436"),
                247: sp.bytes("0x323437"),
                248: sp.bytes("0x323438"),
                249: sp.bytes("0x323439"),
                250: sp.bytes("0x323530"),
                251: sp.bytes("0x323531"),
                252: sp.bytes("0x323532"),
                253: sp.bytes("0x323533"),
                254: sp.bytes("0x323534"),
                255: sp.bytes("0x323535")
            }

        )

        # Build the TZIP-016 contract metadata
        # This is helpful to get the off-chain views code in json format
        contract_metadata = {
            "name": "Extended FA2 template contract with collections",
            "description": "This contract allows for batch minting of collections. "
            "Based on Teia Community extended FA2 contract",
            "version": "v1.0.0",
            "authors": ["Teia Community <https://twitter.com/TeiaCommunity>"],
            "homepage": "https://teia.art",
            "source": {
                "tools": ["SmartPy 0.10.1"],
                "location": "https://github.com/teia-community/teia-smart-contracts/blob/main/python/contracts/fa2.py"
            },
            "interfaces": ["TZIP-012", "TZIP-016"],
            "views": [
                self.get_balance,
                self.total_supply,
                self.all_tokens,
                self.is_operator,
                self.token_metadata,
                self.token_royalties,
                self.last_token_id,
                self.last_collection_id,
                self.all_collections,
                self.list_collection_cids,
                self.collection_first_last_tokens,
            ],
            "permissions": {
                "operator": "owner-or-operator-transfer",
                "receiver": "owner-no-hook",
                "sender": "owner-no-hook"
            }
        }

        self.init_metadata("contract_metadata", contract_metadata)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contract
        administrator.

        """
        sp.verify(sp.sender == self.data.administrator,
                  message="FA2_NOT_ADMIN")

    def check_token_exists(self, token_id):
        """Checks that the given token exists.

        """
        sp.verify(token_id < self.data.counter, message="FA2_TOKEN_UNDEFINED")

    def check_collection_exists(self, collection_id):
        """ Check that the collection exists

        """
        # Check that the collection exists
        sp.verify(collection_id < self.data.collection_counter,
                  message="COLLECTION_UNDEFINED")

    @sp.entry_point
    def mint_collection(self, params):
        """Mints several new tokens at once.
        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            total=sp.TNat,
            base=sp.TBytes,
            royalties=FA2.TOKEN_ROYALTIES_VALUE_TYPE).layout(
                ("total", ("base", "royalties"))))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that the total of tokens minted do not exceed 256
        # as we only have a name map for 0...255
        sp.verify(params.total <= 256, message="FA2_TOTAL_TOO_HIGH")

        # Check that the total royalties do not exceed 100%
        sp.verify(params.royalties.minter.royalties +
                  params.royalties.creator.royalties <= 1000,
                  message="FA2_INVALID_ROYALTIES")

        # the base url is stored once in the collection map for all the tokens in this collection
        collection_id = sp.compute(self.data.collection_counter)

        self.data.collection_base_url[collection_id] = params.base

        self.data.collection_start_id[collection_id] = self.data.counter

        self.data.collection_royalties[collection_id] = params.royalties

        self.data.collection_ledger[collection_id] = params.royalties.minter.address

        current_token = sp.local("current_token", 0)

        # Loop over the total tokens
        # We trust the caller to have uploaded metadata files from /0 to /total
        with sp.while_(current_token.value < params.total):

            token_id = sp.compute(self.data.counter)

            # Store this token collection id to be able to get the base url later
            self.data.token_collection[token_id] = collection_id

            # Increase the tokens counter
            self.data.counter += 1

            # control the loop
            current_token.value += 1

        # Increase the collection counter
        self.data.collection_counter += 1

    @sp.entry_point
    def transfer(self, params):
        """Executes a list of token transfers.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TRecord(
            from_=sp.TAddress,
            txs=sp.TList(sp.TRecord(
                to_=sp.TAddress,
                token_id=sp.TNat,
                amount=sp.TNat).layout(
                    ("to_", ("token_id", "amount"))))).layout(
                        ("from_", "txs"))))

        # Loop over the list of transfers
        with sp.for_("transfer", params) as transfer:
            with sp.for_("tx", transfer.txs) as tx:

                sp.verify(tx.amount < 2, message="FA2_INSUFFICIENT_BALANCE")
                sp.verify(tx.amount != 0, message="FA2_TRANSACTION_ZERO")

                # Check that the token exists
                token_id = sp.compute(tx.token_id)
                self.check_token_exists(token_id)

                declared_owner = sp.compute(transfer.from_)

                # if the token is in the individual tokens ledger...
                with sp.if_(self.data.ledger.contains(token_id)):
                    # ... check that the declared owner actually owns the token
                    sp.verify(self.data.ledger[token_id] == declared_owner,
                              message="FA2_INSUFFICIENT_BALANCE")

                # Else the token is still owned by the original minter
                # We check the collection ledger
                with sp.else_():
                    # Get the collection id from the collection map
                    collection_id = self.data.token_collection[token_id]

                    # Check that the declared owner minted the collection
                    sp.verify(self.data.collection_ledger[collection_id] == declared_owner,
                              message="FA2_INSUFFICIENT_BALANCE")

                # Check that the sender is one of the token operators
                sp.verify(
                    (sp.sender == declared_owner) |
                    self.data.operators.contains(sp.record(
                        owner=declared_owner,
                        operator=sp.sender,
                        token_id=token_id)),
                    message="FA2_NOT_OPERATOR")

                # Add the new owner to the token ledger
                self.data.ledger[token_id] = tx.to_

                # Mark the collection as not fresh anymore
                self.data.collection_not_fresh[collection_id] = sp.unit

    @sp.entry_point
    def transfer_collection(self, params):
        """Executes the transfer of a collection.
        This ONLY transfer fresh, untouched lazy ledger collection,
        at the exclusion of collections that have already transfered tokens 
        (tokens with a traditional ledger entry created)
        The purpose of this limitation is to avoid corner cases and simplify the model:
        you can either transfer 
         - a whole, fresh collection (cheap), 
         - or single tokens (traditional cost)

        This entry point is used by the marketplace contract for bulk swapping a whole collection

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
                    from_=sp.TAddress,
                    to_=sp.TAddress,
                    collection_id=sp.TNat).layout(
                        ("from_", ("to_", "collection_id"))
        )
        )

        # Check that the collection exists
        self.check_collection_exists(params.collection_id)

        # Check that the collection is fresh (no tokens in standard ledger)
        sp.verify(~self.data.collection_not_fresh.contains(params.collection_id),
                  message="COLLECTION_NOT_FRESH_PLEASE_TRANSFER_SINGLE_TOKENS")

        declared_owner = sp.compute(params.from_)

        # Check that the declared owner minted the collection
        sp.verify(self.data.collection_ledger[params.collection_id] == declared_owner,
                  message="COLLECTION_NOT_OWNER")

        # Check that the sender is one of the collection operators
        sp.verify(
            (sp.sender == declared_owner) |
            self.data.collection_operators.contains(sp.record(
                owner=declared_owner,
                operator=sp.sender,
                collection_id=params.collection_id)),
            message="COLLECTION_NOT_OPERATOR")

        # Add the new owner to the token ledger
        self.data.collection_ledger[params.collection_id] = params.to_

    @sp.entry_point
    def balance_of(self, params):
        """Requests information about a list of token balances.

        """
        # Define the input parameter data type
        request_type = sp.TRecord(
            owner=sp.TAddress,
            token_id=sp.TNat).layout(("owner", "token_id"))
        sp.set_type(params, sp.TRecord(
            requests=sp.TList(request_type),
            callback=sp.TContract(sp.TList(sp.TRecord(
                request=request_type,
                balance=sp.TNat).layout(("request", "balance"))))).layout(
                    ("requests", "callback")))

        def process_request(request):
            # Check that the token exists
            self.check_token_exists(request.token_id)

            # Return the owner token balance

            # if the token is in the individual tokens ledger...
            with sp.if_(self.data.ledger.contains(request.token_id)):
                # ... check that the requested owner actually owns the token
                with sp.if_(self.data.ledger[request.token_id] == request.owner):
                    sp.result(sp.record(
                        request=request,
                        balance=1))
                with sp.else_():
                    sp.result(sp.record(
                        request=request,
                        balance=0))

            # Else the token is still owned by the original minter
            # We check the collection ledger
            with sp.else_():
                # Get the collection id from the collection map
                collection_id = self.data.token_collection[request.token_id]
                # Check that the requested owner minted the collection
                with sp.if_(self.data.collection_ledger[collection_id] == request.owner):
                    sp.result(sp.record(
                        request=request,
                        balance=1))
                with sp.else_():
                    sp.result(sp.record(
                        request=request,
                        balance=0))

        sp.transfer(
            params.requests.map(process_request), sp.mutez(0), params.callback)

    @sp.entry_point
    def update_operators(self, params):
        """Updates a list of token operators.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TVariant(
            add_operator=FA2.OPERATOR_KEY_TYPE,
            remove_operator=FA2.OPERATOR_KEY_TYPE)))

        # Loop over the list of update operators
        with sp.for_("update_operator", params) as update_operator:
            with update_operator.match_cases() as arg:
                with arg.match("add_operator") as operator_key:
                    # Check that the token exists
                    self.check_token_exists(operator_key.token_id)

                    # Check that the sender is the token owner
                    sp.verify(sp.sender == operator_key.owner,
                              message="FA2_SENDER_IS_NOT_OWNER")

                    # Add the new operator to the operators big map
                    self.data.operators[operator_key] = sp.unit
                with arg.match("remove_operator") as operator_key:
                    # Check that the token exists
                    self.check_token_exists(operator_key.token_id)

                    # Check that the sender is the token owner
                    sp.verify(sp.sender == operator_key.owner,
                              message="FA2_SENDER_IS_NOT_OWNER")

                    # Remove the operator from the operators big map
                    del self.data.operators[operator_key]

    @sp.entry_point
    def update_collection_operators(self, params):
        """Updates a list of collection operators.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TVariant(
            add_operator=FA2.COLLECTION_OPERATOR_KEY_TYPE,
            remove_operator=FA2.COLLECTION_OPERATOR_KEY_TYPE)))

        # Loop over the list of update operators
        with sp.for_("update_operator", params) as update_operator:
            with update_operator.match_cases() as arg:
                with arg.match("add_operator") as operator_key:
                    # Check that the token exists
                    self.check_collection_exists(operator_key.collection_id)

                    # Check that the sender is the token owner
                    sp.verify(sp.sender == operator_key.owner,
                              message="FA2_SENDER_IS_NOT_OWNER")

                    # Add the new operator to the operators big map
                    self.data.collection_operators[operator_key] = sp.unit
                with arg.match("remove_operator") as operator_key:
                    # Check that the token exists
                    self.check_collection_exists(operator_key.collection_id)

                    # Check that the sender is the token owner
                    sp.verify(sp.sender == operator_key.owner,
                              message="FA2_SENDER_IS_NOT_OWNER")

                    # Remove the operator from the operators big map
                    del self.data.collection_operators[operator_key]

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contract administrator to another address.

        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contract administrator
        responsibilities.

        """
        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(
            message="FA2_NO_NEW_ADMIN"), message="FA2_NOT_PROPOSED_ADMIN")

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.entry_point
    def set_metadata(self, params):
        """Updates the contract metadata.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            k=sp.TString,
            v=sp.TBytes).layout(("k", "v")))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Update the contract metadata
        self.data.metadata[params.k] = params.v

    @sp.onchain_view(pure=True)
    def token_exists(self, token_id):
        """Checks if the token exists.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return true if the token exists
        sp.result(token_id < self.data.counter)

    @sp.onchain_view(pure=True)
    def last_token_id(self):
        """Returns the last token id.

            The counter is incremented just after minting,
            and thus it is 1-indexed: it always equal the number of tokens
            but tokens ids are 0-indexed, so we substract 1

        """
        sp.verify(self.data.counter > 0, message="FA2_NO_TOKEN")
        sp.result(sp.as_nat(self.data.counter - 1))

    @sp.onchain_view(pure=True)
    def get_balance(self, params):
        """Returns the owner token balance.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            owner=sp.TAddress,
            token_id=sp.TNat).layout(("owner", "token_id")))

        # Check that the token exists
        self.check_token_exists(params.token_id)

        # Return the owner token balance

        # if the token is in the individual tokens ledger...
        with sp.if_(self.data.ledger.contains(params.token_id)):
            # ... check that the requested owner actually owns the token
            with sp.if_(self.data.ledger[params.token_id] == params.owner):
                sp.result(1)
            with sp.else_():
                sp.result(0)

        # Else the token is still owned by the original minter
        # We check the collection ledger
        with sp.else_():
            # Get the collection id from the collection map
            collection_id = self.data.token_collection[params.token_id]
            # Check that the requested owner minted the collection
            with sp.if_(self.data.collection_ledger[collection_id] == params.owner):
                sp.result(1)
            with sp.else_():
                sp.result(0)

    @sp.onchain_view(pure=True)
    def total_supply(self, token_id):
        """Returns the total supply for a given token id.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Check that the token exists
        self.check_token_exists(token_id)

        # Return the token total supply
        sp.result(1)

    @sp.onchain_view(pure=True)
    def all_tokens(self):
        """Returns a list with all the token ids.

        """
        sp.result(sp.range(0, self.data.counter))

    @sp.onchain_view(pure=True)
    def is_operator(self, params):
        """Checks if a given token operator exists.

        """
        # Define the input parameter data type
        sp.set_type(params, FA2.OPERATOR_KEY_TYPE)

        # Check that the token exists
        self.check_token_exists(params.token_id)

        # Return true if the token operator exists
        sp.result(self.data.operators.contains(params))

    @sp.onchain_view(pure=True)
    def is_collection_operator(self, params):
        """Checks if a given collection operator exists.

        """
        # Define the input parameter data type
        sp.set_type(params, FA2.COLLECTION_OPERATOR_KEY_TYPE)

        # Check that the collection exists
        self.check_collection_exists(params.collection_id)

        # Return true if the operator exists
        sp.result(self.data.collection_operators.contains(params))

    @sp.onchain_view(pure=True)
    def token_metadata(self, token_id):
        """Returns the token metadata.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Check that the token exists
        self.check_token_exists(token_id)

        # Get the collection id from the collection map
        collection_id = self.data.token_collection[token_id]

        base = self.data.collection_base_url[collection_id]

        collection_start_id = self.data.collection_start_id[collection_id]

        # examples: 78 - 0 (first collection) = 78 ; 256 - 256 = 0 ; 266 - 256 = 10
        name = self.data.token_name_map[sp.as_nat(
            token_id - collection_start_id)]

        token_metadata_record = sp.record(
            token_id=token_id,
            token_info={"": base+name}
        )

        # Return the token metadata
        sp.result(token_metadata_record)

    @sp.onchain_view(pure=True)
    def token_royalties(self, token_id):
        """Returns the token royalties information.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Get the collection id from the collection map
        collection_id = self.data.token_collection[token_id]

        # Return the token royalties information
        sp.result(self.data.collection_royalties[collection_id])

    ## Collection views ##

    def check_minted_at_least_one_collection(self):
        # Checks that the contract has been used for minting at least one collection
        sp.verify(self.data.collection_counter > 0,
                  message="NO_COLLECTION_MINTED_EMPTY_CONTRACT")

    @sp.onchain_view(pure=True)
    def last_collection_id(self):
        """Returns the last collection id.

            The counter is incremented after minting, and thus 1-indexed
            but collections are 0-indexed

        """
        self.check_minted_at_least_one_collection()

        sp.result(self.data.collection_counter - 1)

    @sp.onchain_view(pure=True)
    def all_collections(self):
        """Returns a list with all the collection ids.

        """
        self.check_minted_at_least_one_collection()
        # sp.range returns first included, last excluded
        sp.result(sp.range(0, self.data.collection_counter))

    @sp.onchain_view(pure=True)
    def list_collection_cids(self, params):
        """Returns collection base CIDs between start (first collection index) and end (last collection index)

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(start=sp.TNat, end=sp.TNat)).layout(
            ("start", "end"))

        COLLECTIONID_AND_CID_TYPE = sp.TRecord(
            collectionid=sp.TNat,
            cid=sp.TBytes,
        ).layout(("collectionid", "cid"))

        self.check_minted_at_least_one_collection()

        # cids are stored as hex encoded bytes from utf8 strings
        collection_cids_set = sp.local(
            "collection_cids_set", sp.set(l=[], t=COLLECTIONID_AND_CID_TYPE))

        # the counter is incremented after minting, and thus 1-indexed
        # but collections are 0-indexed
        last_collection_index = sp.as_nat(self.data.collection_counter - 1)

        start = sp.local("start", 0)
        end = sp.local("end", 0)

        # Check the start collection is not beyond the last collection
        sp.verify(params.start <= last_collection_index,
                  message="START_IS_BEYOND_LAST_COLLECTION")

        start.value = params.start

        # Capping end to last collection => TO TEST
        with sp.if_(params.end > self.data.collection_counter):
            end.value = last_collection_index
        with sp.else_():
            end.value = params.end

        # Check if start collection is beyond last collection
        sp.verify(start.value <= end.value,
                  message="RANGE_INVERTED_START_GREATER_THAN_END")

        # could return just one collection if start == end
        # sp.range is (inclusive, exclusive)
        all_collection_ids = sp.range(start.value, end.value + 1)

        with sp.for_("collection_id", all_collection_ids) as collection_id:

            base_cid = self.data.collection_base_url[collection_id]

            collection_cids_set.value.add(sp.record(
                collectionid=collection_id,
                cid=base_cid))

        # Return the token metadata
        sp.result(collection_cids_set.value)

    @sp.onchain_view(pure=True)
    def collection_first_last_tokens(self, collection_id):
        """Returns the first and last token ids for a collection.

        """
        # Define the input parameter data type
        sp.set_type(collection_id, sp.TNat)

        # Check that the collection exists
        sp.verify(collection_id < self.data.collection_counter,
                  message="COLLECTION_UNDEFINED")

        collection_start_token_id = self.data.collection_start_id[collection_id]

        collection_end_token_id = sp.local("collection_end_id", 0)

        # Check if this is the last collection
        with sp.if_(collection_id == sp.as_nat(self.data.collection_counter - 1)):
            # then the last token id of the collection is... the last token id
            collection_end_token_id.value = sp.as_nat(self.data.counter - 1)
        with sp.else_():
            # else the last token id of the collection is one before the next collection's first token
            collection_end_token_id.value = sp.as_nat(
                self.data.collection_start_id[collection_id+1] - 1)

        # Return the token metadata
        sp.result(sp.record(
                  first=collection_start_token_id,
                  last=collection_end_token_id.value)
                  )

    @sp.onchain_view(pure=True)
    def get_token_collection_id(self, token_id):
        """Returns the first and last token ids for a collection.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return the collection id from the collection map
        sp.result(self.data.token_collection[token_id])


sp.add_compilation_target("fa2", FA2(
    administrator=sp.address("tz1ahsDNFzukj51hVpW626qH7Ug9HeUVQDNG"),
    metadata=sp.utils.metadata_of_url("ipfs://bafkreibcagociaxq4eihkrlc5grdgt657t5mgji6lrraszfeaenke4eleq")))
