import smartpy as sp


class DAOGovernance(sp.Contract):
    """This contract implements a Decentralized Autonomous Organization (DAO)
    governed by DAO token holders and community representatives.

    The contract is a combination of the Teia multisig wallet contract that the
    Murmuration DAO smart contracts:
      https://github.com/teia-community/teia-smart-contracts
      https://github.com/Hover-Labs/murmuration

    Main features:
        - It considers two kinds of DAO members: DAO token holders and
          community representatives.
        - Many proposals can run at the same time.
        - Members do not need to escrow their DAO tokens for voting, only to
          create proposals.
        - It uses on-chain views instead of callback functions to access DAO
          token balances.
        - DAO governance parameters can be updated via lambda proposals.
        - Separates the DAO governance from the DAO treasury.

    """

    GOVERNANCE_PARAMETERS_TYPE = sp.TRecord(
        # The proposal voting period in days
        voting_period=sp.TNat,
        # The amount of DAO tokens to escrow to create a proposal
        escrow_amount=sp.TNat,
        # The percentage of positive votes needed to return the tokens in escrow
        escrow_return=sp.TNat,
        # The percentage of positive votes needed to reach super-majority
        supermajority=sp.TNat,
        # The representatives vote share percentage relative to the quorum
        representatives_share=sp.TNat,
        # The minimum perion between quorum updates in days
        quorum_update_period=sp.TNat,
        # The minimum possible quorum value
        min_quorum=sp.TNat,
        # The maximum possible quorum value
        max_quorum=sp.TNat).layout(
            ("voting_period", ("escrow_amount", ("escrow_return", ("supermajority", ("representatives_share", ("quorum_update_period", ("min_quorum", "max_quorum"))))))))

    PROPOSAL_KIND_TYPE = sp.TVariant(
        # A proposal in the form of text to be voted for
        text=sp.TUnit,
        # A proposal to transfer mutez from the DAO treasury to other accounts
        transfer_mutez=sp.TUnit,
        # A proposal to transfer a token from the DAO treasury to other accounts
        transfer_token=sp.TUnit,
        # A proposal to execute a lambda function
        lambda_function=sp.TUnit)

    MUTEZ_TRANSFERS_TYPE = sp.TList(sp.TRecord(
        # The amount of mutez to transfer
        amount=sp.TMutez,
        # The transfer destination
        destination=sp.TAddress).layout(
            ("amount", "destination")))

    TOKEN_TRANSFERS_TYPE = sp.TRecord(
        # The token contract address
        fa2=sp.TAddress,
        # The token id
        token_id=sp.TNat,
        # The token transfer distribution
        distribution=sp.TList(sp.TRecord(
            # The number of token editions to transfer
            amount=sp.TNat,
            # The transfer destination
            destination=sp.TAddress).layout(("amount", "destination")))).layout(
                ("fa2", ("token_id", "distribution")))

    LAMBDA_FUNCTION_TYPE = sp.TLambda(sp.TUnit, sp.TList(sp.TOperation))

    PROPOSAL_PARAMETERS_TYPE = sp.TRecord(
        # The list of mutez transfers
        mutez_transfers=sp.TOption(MUTEZ_TRANSFERS_TYPE),
        # The list of token transfers
        token_transfers=sp.TOption(TOKEN_TRANSFERS_TYPE),
        # The lambda function to execute
        lambda_function=sp.TOption(LAMBDA_FUNCTION_TYPE)).layout(
            ("mutez_transfers", ("token_transfers", "lambda_function")))

    PROPOSAL_STATUS_TYPE = sp.TVariant(
        # The status for proposals that are open and can still be voted
        open=sp.TUnit,
        # The status for proposals that have been approved but not yet executed
        approved=sp.TUnit,
        # The status for approved and executed proposals
        executed=sp.TUnit,
        # The status for proposals that didn't receive enough votes to be
        # approved and executed
        rejected=sp.TUnit)

    PROPOSAL_TYPE = sp.TRecord(
        # The kind of proposal: text, transfer_mutez, transfer_token, etc
        kind=PROPOSAL_KIND_TYPE,
        # The proposal title
        title=sp.TBytes,
        # The proposal description (normally an link to a file stored in IPFS)
        description=sp.TBytes,
        # The proposal parameters
        parameters=PROPOSAL_PARAMETERS_TYPE,
        # The DAO member that submitted the proposal
        issuer=sp.TAddress,
        # The timestamp when the proposal was submitted
        timestamp=sp.TTimestamp,
        # The block level when the proposal was submitted
        level=sp.TNat,
        # The amount of DAO tokens in escrow
        escrow_amount=sp.TNat,
        # The proposal current status: open, approved, executed or rejected
        status=PROPOSAL_STATUS_TYPE).layout(
            ("kind", ("title", ("description", ("parameters", ("issuer", ("timestamp", ("level", ("escrow_amount", "status")))))))))

    VOTES_SUMMARY_TYPE = sp.TRecord(
        # The number of positive votes that the proposal has received
        positive=sp.TNat,
        # The number of negative votes that the proposal has received
        negative=sp.TNat,
        # The number of abstain votes that the proposal has received
        abstain=sp.TNat,
        # The total number of votes that the proposal has received
        total=sp.TNat,
        # The total number of wallets that voted
        participation=sp.TNat).layout(
            ("positive", ("negative", ("abstain", ("total", "participation")))))

    VOTE_KIND_TYPE = sp.TVariant(
        # A positive vote
        yes=sp.TUnit,
        # A negative vote
        no=sp.TUnit,
        # An abstain vote
        abstain=sp.TUnit)

    VOTE_TYPE = sp.TRecord(
        # The user vote: yes, no or abstain
        vote=VOTE_KIND_TYPE,
        # The vote weight based on the DAO token balance (0 for representatives)
        weight=sp.TNat).layout(
            ("vote", "weight"))

    FA2_TRANSFER_TYPE = sp.TList(sp.TRecord(
        # The address that sends the token editions
        from_=sp.TAddress,
        # The list of token trasfers
        txs=sp.TList(sp.TRecord(
            # The token destination
            to_=sp.TAddress,
            # The token id
            token_id=sp.TNat,
            # The number of token editions
            amount=sp.TNat).layout(("to_", ("token_id", "amount"))))).layout(
                ("from_", "txs")))

    def __init__(self, metadata, treasury, token, representatives, quorum,
                 governance_parameters):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The DAO treasury contract address
            treasury=sp.TAddress,
            # The DAO token contract address
            token=sp.TAddress,
            # The community representatives contract address
            representatives=sp.TAddress,
            # The minimum number of votes needed to approve proposals
            quorum=sp.TNat,
            # The last quorum update
            last_quorum_update=sp.TTimestamp,
            # The DAO governance parameters
            governance_parameters=DAOGovernance.GOVERNANCE_PARAMETERS_TYPE,
            # The big map with the proposals information
            proposals=sp.TBigMap(sp.TNat, DAOGovernance.PROPOSAL_TYPE),
            # The big map with the DAO token holders vote summaries
            token_votes=sp.TBigMap(sp.TNat, DAOGovernance.VOTES_SUMMARY_TYPE),
            # The big map with the community representatives vote summaries
            representatives_votes=sp.TBigMap(
                sp.TNat, DAOGovernance.VOTES_SUMMARY_TYPE),
            # The big map with all the votes information
            votes=sp.TBigMap(
                sp.TPair(sp.TNat, sp.TAddress), DAOGovernance.VOTE_TYPE),
            # The proposals counter
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
            treasury=treasury,
            token=token,
            representatives=representatives,
            quorum=quorum,
            last_quorum_update=sp.now,
            governance_parameters=governance_parameters,
            proposals=sp.big_map(),
            token_votes=sp.big_map(),
            representatives_votes=sp.big_map(),
            votes=sp.big_map(),
            counter=0)

    def get_token_balance(self):
        """Gets the sender token balance calling the DAO token on-chain view.

        """
        return sp.view(
            name="get_balance",
            address=self.data.token,
            param=sp.record(owner=sp.sender, token_id=sp.nat(0)),
            t=sp.TNat).open_some()

    def get_prior_token_balance(self, level, max_checkpoints):
        """Gets the sender prior token balance calling the DAO token on-chain
        view.

        """
        return sp.view(
            name="get_prior_balance",
            address=self.data.token,
            param=sp.record(
                owner=sp.sender, level=level, max_checkpoints=max_checkpoints),
            t=sp.TNat).open_some()

    def transfer_tokens(self, from_, to_, amount):
        """Transfers a given amount of DAO tokens.

        """
        # Get a handle to the DAO token transfer entry point
        transfer_handle = sp.contract(
            t=DAOGovernance.FA2_TRANSFER_TYPE,
            address=self.data.token,
            entry_point="transfer").open_some()

        # Execute the tranfer
        sp.transfer(
            arg=[sp.record(
                from_=from_,
                txs=[sp.record(
                    to_=to_,
                    token_id=sp.nat(0),
                    amount=amount)])],
            amount=sp.mutez(0),
            destination=transfer_handle)

    @sp.entry_point
    def create_proposal(self, params):
        """Creates a new DAO proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            kind=DAOGovernance.PROPOSAL_KIND_TYPE,
            title=sp.TBytes,
            description=sp.TBytes,
            parameters=DAOGovernance.PROPOSAL_PARAMETERS_TYPE).layout(
                ("kind", ("title", ("description", "parameters")))))

        # Check that the proposal contains the correct parameters
        valid_parameters = sp.local("valid_parameters", False)

        with params.kind.match_cases() as arg:
            with arg.match("text"):
                valid_parameters.value = (
                    ~params.parameters.mutez_transfers.is_some() & 
                    ~params.parameters.token_transfers.is_some() & 
                    ~params.parameters.lambda_function.is_some())
            with arg.match("transfer_mutez"):
                valid_parameters.value = (
                    params.parameters.mutez_transfers.is_some() & 
                    ~params.parameters.token_transfers.is_some() & 
                    ~params.parameters.lambda_function.is_some())
            with arg.match("transfer_token"):
                valid_parameters.value = (
                    ~params.parameters.mutez_transfers.is_some() & 
                    params.parameters.token_transfers.is_some() & 
                    ~params.parameters.lambda_function.is_some())
            with arg.match("lambda_function"):
                valid_parameters.value = (
                    ~params.parameters.mutez_transfers.is_some() & 
                    ~params.parameters.token_transfers.is_some() & 
                    params.parameters.lambda_function.is_some())

        sp.verify(valid_parameters.value, message="DAO_WRONG_PARAMETERS")

        # Check if it's necessary to escrow DAO tokens to create proposals
        with sp.if_(self.data.governance_parameters.escrow_amount > 0):
            # Transfer the DAO tokens from the sender to the DAO contract
            self.transfer_tokens(
                from_=sp.sender,
                to_=sp.self_address,
                amount=self.data.governance_parameters.escrow_amount)
        with sp.else_():
            # Check that one of the DAO members executed the entry point
            sp.verify(self.get_token_balance() > 0, message="DAO_NOT_MEMBER")

        # Add the new proposal information to the proposals big map
        self.data.proposals[self.data.counter] = sp.record(
            kind=params.kind,
            title=params.title,
            description=params.description,
            parameters=params.parameters,
            issuer=sp.sender,
            timestamp=sp.now,
            level=sp.level,
            escrow_amount=self.data.governance_parameters.escrow_amount,
            status=sp.variant("open", sp.unit))

        # Initialize DAO token holders vote counters for the new proposal
        self.data.token_votes[self.data.counter] = sp.record(
            positive=0,
            negative=0,
            abstain=0,
            total=0,
            participation=0)

        # Initialize representatives vote counters for the new proposal
        self.data.representatives_votes[self.data.counter] = sp.record(
            positive=0,
            negative=0,
            abstain=0,
            total=0,
            participation=0)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def token_vote(self, params):
        """Adds a new DAO token holder vote for a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            vote=DAOGovernance.VOTE_KIND_TYPE,
            max_checkpoints=sp.TOption(sp.TNat)).layout(
                ("proposal_id", ("vote", "max_checkpoints"))))

        # Check that the proposal exists
        sp.verify(params.proposal_id < self.data.counter,
                  message="DAO_INEXISTENT_PROPOSAL")

        # Check that the proposal voting period didn't expire
        proposal = sp.compute(self.data.proposals[params.proposal_id])
        end_date = proposal.timestamp.add_days(
            sp.to_int(self.data.governance_parameters.voting_period))
        sp.verify(sp.now < end_date, message="DAO_CLOSED_PROPOSAL")

        # Check that the member didn't vote the proposal before
        vote_key = sp.pair(params.proposal_id, sp.sender)
        sp.verify(~self.data.votes.contains(vote_key),
                  message="DAO_ALREADY_VOTED")

        # Get the member DAO token balance at the proposal creation
        token_balance = sp.local("token_balance", self.get_prior_token_balance(
            proposal.level, params.max_checkpoints))

        # Add the amount of tokens in escrow if the voter is the proposal issuer
        with sp.if_(sp.sender == proposal.issuer):
            token_balance.value += proposal.escrow_amount

        # Check that the token balance is not zero
        sp.verify(token_balance.value > 0, message="DAO_ZERO_BALANCE")

        # Calculate the voting weight (for the moment we assume linear weight)
        weight = token_balance.value

        # Update the DAO token holders vote summary
        new_votes = sp.local(
            "new_votes", self.data.token_votes[params.proposal_id])
        new_votes.value.total += weight
        new_votes.value.participation += 1

        with params.vote.match_cases() as arg:
            with arg.match("yes"):
                new_votes.value.positive += weight
            with arg.match("no"):
                new_votes.value.negative += weight
            with arg.match("abstain"):
                new_votes.value.abstain += weight

        self.data.token_votes[params.proposal_id] = new_votes.value

        # Add the vote to the votes big map
        self.data.votes[vote_key] = sp.record(vote=params.vote, weight=weight)

    @sp.entry_point
    def representatives_vote(self, params):
        """Adds a new representative vote for a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            vote=DAOGovernance.VOTE_KIND_TYPE,
            representative=sp.TAddress).layout(
                ("proposal_id", ("vote", "representative"))))

        # Check that the representatives contract executed the entry point
        sp.verify(sp.sender == self.data.representatives,
                  message="DAO_NOT_REPRESENTATIVES")

        # Check that the proposal exists
        sp.verify(params.proposal_id < self.data.counter,
                  message="DAO_INEXISTENT_PROPOSAL")

        # Check that the proposal voting period didn't expire
        end_date = self.data.proposals[params.proposal_id].timestamp.add_days(
            sp.to_int(self.data.governance_parameters.voting_period))
        sp.verify(sp.now < end_date, message="DAO_CLOSED_PROPOSAL")

        # Check that the representative didn't vote the proposal before
        vote_key = sp.pair(params.proposal_id, params.representative)
        sp.verify(~self.data.votes.contains(vote_key),
                  message="DAO_ALREADY_VOTED")

        # Update the representatives vote summary
        new_votes = sp.local(
            "new_votes", self.data.representatives_votes[params.proposal_id])
        new_votes.value.total += 1
        new_votes.value.participation += 1

        with params.vote.match_cases() as arg:
            with arg.match("yes"):
                new_votes.value.positive += 1
            with arg.match("no"):
                new_votes.value.negative += 1
            with arg.match("abstain"):
                new_votes.value.abstain += 1

        self.data.representatives_votes[params.proposal_id] = new_votes.value

        # Add the vote to the votes big map
        self.data.votes[vote_key] = sp.record(vote=params.vote, weight=0)

    @sp.entry_point
    def evaluate_voting_result(self, proposal_id):
        """Evaluates the voting result of a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that one of the DAO members executed the entry point
        sp.verify(self.get_token_balance() > 0, message="DAO_NOT_MEMBER")

        # Check that the proposal exists
        sp.verify(proposal_id < self.data.counter,
                  message="DAO_INEXISTENT_PROPOSAL")

        # Check that the proposal status is still set as open
        proposal = sp.compute(self.data.proposals[proposal_id])
        sp.verify(proposal.status.is_variant("open"),
                  message="DAO_STATUS_NOT_OPEN")

        # Check that the proposal voting period has finished
        end_date = proposal.timestamp.add_days(
            sp.to_int(self.data.governance_parameters.voting_period))
        sp.verify(sp.now > end_date, message="DAO_OPEN_PROPOSAL")

        # Get the votes summaries for the DAO token holders and representatives
        token_votes = sp.compute(self.data.token_votes[proposal_id])
        representatives_votes = sp.compute(self.data.representatives_votes[proposal_id])

        # Calculate the representatives votes based on the current quorum
        representatives_total = sp.compute(self.data.quorum * self.data.governance_parameters.representatives_share) // 100
        representatives_positive = (representatives_total * representatives_votes.positive) // representatives_votes.total
        representatives_negative = (representatives_total * representatives_votes.negative) // representatives_votes.total

        # Count the total votes
        total = token_votes.total + representatives_total
        positive = sp.compute(token_votes.positive + representatives_positive)
        negative = sp.compute(token_votes.negative + representatives_negative)

        # Check if there are some DAO tokens in escrow
        with sp.if_(proposal.escrow_amount > 0):
            # Check which address should receive the DAO tokens
            receiver = sp.local("receiver", proposal.issuer)
            keep_scrow = positive < (((positive + negative) * self.data.governance_parameters.escrow_return) // 100)

            with sp.if_(keep_scrow):
                receiver.value = self.data.treasury

            # Transfer the DAO tokens
            self.transfer_tokens(
                from_=sp.self_address,
                to_=receiver.value,
                amount=proposal.escrow_amount)

        # Check if the proposal passed the required thresholds to be approved
        passed_supermajority = positive >= (((positive + negative) * self.data.governance_parameters.supermajority) // 100)
        passed_quorum = total >= self.data.quorum

        # Set the proposal as approved or rejected depending of the result
        with sp.if_(passed_supermajority & passed_quorum):
            self.data.proposals[proposal_id].status = sp.variant("approved", sp.unit)
        with sp.else_():
            self.data.proposals[proposal_id].status = sp.variant("rejected", sp.unit)

        # Check if the quorum can be updated
        min_quorum_update_date = self.data.last_quorum_update.add_days(
            sp.to_int(self.data.governance_parameters.quorum_update_period))

        with sp.if_(sp.now > min_quorum_update_date):
            # Calculate the new quorum value
            new_quorum = sp.local("new_quorum", (self.data.quorum * 80 + total * 20) // 100)

            with sp.if_(new_quorum.value < self.data.governance_parameters.min_quorum):
                new_quorum.value = self.data.governance_parameters.min_quorum

            with sp.if_(new_quorum.value > self.data.governance_parameters.max_quorum):
                new_quorum.value = self.data.governance_parameters.max_quorum

            # Update the quorum parameters
            self.data.quorum = new_quorum.value
            self.data.last_quorum_update = sp.now

    @sp.entry_point
    def execute_proposal(self, proposal_id):
        """Executes a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that one of the DAO members executed the entry point
        sp.verify(self.get_token_balance() > 0, message="DAO_NOT_MEMBER")

        # Check that the proposal exists
        sp.verify(proposal_id < self.data.counter,
                  message="DAO_INEXISTENT_PROPOSAL")

        # Check that the proposal is approved
        proposal = sp.compute(self.data.proposals[proposal_id])
        sp.verify(proposal.status.is_variant("approved"),
                  message="DAO_STATUS_NOT_APPROVED")

        # Execute the proposal
        self.data.proposals[proposal_id].status = sp.variant(
            "executed", sp.unit)

        with sp.if_(proposal.kind.is_variant("transfer_mutez")):
            # Get a handle to the DAO treasury transfer mutez entry point
            transfer_mutez_handle = sp.contract(
                t=DAOGovernance.MUTEZ_TRANSFERS_TYPE,
                address=self.data.treasury,
                entry_point="transfer_mutez").open_some()

            # Execute the tranfer
            sp.transfer(
                arg=proposal.parameters.mutez_transfers.open_some(),
                amount=sp.mutez(0),
                destination=transfer_mutez_handle)

        with sp.if_(proposal.kind.is_variant("transfer_token")):
            # Get a handle to the DAO treasury transfer token entry point
            transfer_token_handle = sp.contract(
                t=DAOGovernance.TOKEN_TRANSFERS_TYPE,
                address=self.data.treasury,
                entry_point="transfer_token").open_some()

            # Execute the tranfer
            sp.transfer(
                arg=proposal.parameters.token_transfers.open_some(),
                amount=sp.mutez(0),
                destination=transfer_token_handle)

        with sp.if_(proposal.kind.is_variant("lambda_function")):
            # Execute the lambda function
            operations = proposal.parameters.lambda_function.open_some()(sp.unit)
            sp.add_operations(operations)

    @sp.entry_point
    def set_treasury(self, new_treasury):
        """Updates the DAO treasury contract address.

        """
        # Define the input parameter data type
        sp.set_type(new_treasury, sp.TAddress)

        # Check that the DAO itself executed the entry point
        sp.verify(sp.sender == sp.self_address, message="DAO_NOT_DAO")

        # Update the DAO treasury contract address
        self.data.treasury = new_treasury

    @sp.entry_point
    def set_representatives(self, new_representatives):
        """Updates the community representatives contract address.

        """
        # Define the input parameter data type
        sp.set_type(new_representatives, sp.TAddress)

        # Check that the DAO or the representatives executed the entry point
        sp.verify((sp.sender == sp.self_address) |
                  (sp.sender == self.data.representatives),
                  message="DAO_NOT_DAO_OR_REPRESENTATIVES")

        # Update the representatives contract address
        self.data.representatives = new_representatives

    @sp.entry_point
    def set_governance_parameters(self, new_governance_parameters):
        """Updates the DAO governance parameters.

        """
        # Define the input parameter data type
        sp.set_type(new_governance_parameters,
                    DAOGovernance.GOVERNANCE_PARAMETERS_TYPE)

        # Check that the DAO itself executed the entry point
        sp.verify(sp.sender == sp.self_address, message="DAO_NOT_DAO")

        # Update the governance parameters
        self.data.governance_parameters = new_governance_parameters

    @sp.onchain_view()
    def get_proposal_count(self):
        """Returns the total number of proposals.

        """
        sp.result(self.data.counter)

    @sp.onchain_view()
    def get_proposal(self, proposal_id):
        """Returns the complete information from a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(proposal_id),
                  message="DAO_INEXISTENT_PROPOSAL")

        # Return the proposal information
        sp.result(self.data.proposals[proposal_id])

    @sp.onchain_view()
    def get_vote(self, params):
        """Returns a member's vote.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            member=sp.TAddress).layout(("proposal_id", "member")))

        # Check that the vote is present in the votes big map
        vote_key = sp.pair(params.proposal_id, params.member)
        sp.verify(self.data.votes.contains(vote_key),
                  message="DAO_NO_MEMBER_VOTE")

        # Return the member's vote
        sp.result(self.data.votes[vote_key])

    @sp.onchain_view()
    def has_voted(self, params):
        """Returns true if the member has voted the given proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            member=sp.TAddress).layout(("proposal_id", "member")))

        # Return true if the member has voted the proposal
        sp.result(self.data.votes.contains((params.proposal_id, params.member)))


sp.add_compilation_target("dao", DAOGovernance(
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    treasury=sp.address("KT1QmSmQ8Mj8JHNKKQmepFqQZy7kDWQ1ekaa"),
    token=sp.address("KT1QmSmQ8Mj8JHNKKQmepFqQZy7kDWQ1ekbb"),
    representatives=sp.address("KT1QmSmQ8Mj8JHNKKQmepFqQZy7kDWQ1ekcc"),
    quorum=8000,
    governance_parameters=sp.record(
        voting_period=5,
        escrow_amount=100,
        escrow_return=30,
        supermajority=70,
        representatives_share=30,
        quorum_update_period=10,
        min_quorum=1000,
        max_quorum=100000)))