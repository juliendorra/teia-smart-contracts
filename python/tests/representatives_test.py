"""Unit tests for the Representatives contract class.

"""

import smartpy as sp

# Import the representatives and fa2 contract modules
representativesModule = sp.io.import_script_from_url("file:contracts/representatives.py")
fa2Module = sp.io.import_script_from_url("file:hen-contracts/fa2.py")


class Recipient(sp.Contract):
    """This contract simulates a user that can recive tez transfers.

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


class Dummy(sp.Contract):
    """This is a dummy contract to be used only for test purposes.

    """

    def __init__(self):
        """Initializes the contract.

        """
        self.init(x=sp.nat(0), y=sp.nat(0))

    @sp.entry_point
    def update_x(self, x):
        """Updates the x value.

        """
        self.data.x = x

    @sp.entry_point
    def update_y(self, y):
        """Updates the y value.

        """
        self.data.y = y


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")
    user4 = sp.test_account("user4")
    non_user = sp.test_account("non_user")
    dao = sp.test_account("dao")

    # Initialize the representatives contract
    representatives = representativesModule.Representatives(
        metadata=sp.utils.metadata_of_url("ipfs://aaa"),
        users=sp.set([user1.address, user2.address, user3.address, user4.address]),
        dao=dao.address,
        minimum_votes=3,
        expiration_time=3)
    representatives.set_initial_balance(sp.tez(10))
    scenario += representatives

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "user1" : user1,
        "user2" : user2,
        "user3" : user3,
        "user4" : user4,
        "user4" : user4,
        "non_user" : non_user,
        "dao": dao,
        "representatives" : representatives}

    return testEnvironment


@sp.add_test(name="Test default entripoint")
def test_default_entripoint():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    non_user = testEnvironment["non_user"]
    representatives = testEnvironment["representatives"]

    # Check that representatives can send tez to the contract
    representatives.default(sp.unit).run(sender=user1, amount=sp.tez(3))

    # Check that the tez are now part of the contract balance
    scenario.verify(representatives.balance == sp.tez(10 + 3))

    # Check that non-representatives can also send tez to the contract
    representatives.default(sp.unit).run(sender=non_user, amount=sp.tez(5))

    # Check that the tez have been added to the contract balance
    scenario.verify(representatives.balance == sp.tez(10 + 3 + 5))


@sp.add_test(name="Test create vote and execute proposal")
def test_create_vote_and_execute_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    non_user = testEnvironment["non_user"]
    representatives = testEnvironment["representatives"]

    # Check that we have the expected users in the representatives contract
    scenario.verify(representatives.is_user(user1.address))
    scenario.verify(representatives.is_user(user2.address))
    scenario.verify(representatives.is_user(user3.address))
    scenario.verify(representatives.is_user(user4.address))
    scenario.verify(~representatives.is_user(non_user.address))
    scenario.verify(sp.len(representatives.get_users()) == 4)

    # Check that we start with zero proposals
    scenario.verify(representatives.data.counter == 0)
    scenario.verify(representatives.get_proposal_count() == 0)

    # Check that only users can submit proposals
    representatives.add_user_proposal(non_user.address).run(valid=False, sender=non_user)

    # Create the add user proposal with one of the representatives
    representatives.add_user_proposal(non_user.address).run(sender=user1)

    # Check that the proposal has been added to the proposals big map
    scenario.verify(representatives.data.proposals.contains(0))
    scenario.verify(representatives.data.counter == 1)
    scenario.verify(representatives.get_proposal_count() == 1)
    scenario.verify(representatives.data.proposals[0].positive_votes == 0)
    scenario.verify(representatives.get_proposal(0).positive_votes == 0)
    scenario.verify(~representatives.data.proposals[0].executed)
    scenario.verify(~representatives.get_proposal(0).executed)

    # The first 3 users vote the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user3)

    # Check that the non-user cannot vote the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(valid=False, sender=non_user)

    # Check that the votes have been added to the votes big map
    scenario.verify(representatives.data.votes[(0, user1.address)] == True)
    scenario.verify(representatives.data.votes[(0, user2.address)] == True)
    scenario.verify(representatives.data.votes[(0, user3.address)] == False)
    scenario.verify(representatives.get_vote(sp.record(proposal_id=0, user=user1.address)) == True)
    scenario.verify(representatives.get_vote(sp.record(proposal_id=0, user=user2.address)) == True)
    scenario.verify(representatives.get_vote(sp.record(proposal_id=0, user=user3.address)) == False)
    scenario.verify(representatives.has_voted(sp.record(proposal_id=0, user=user1.address)))
    scenario.verify(representatives.has_voted(sp.record(proposal_id=0, user=user2.address)))
    scenario.verify(representatives.has_voted(sp.record(proposal_id=0, user=user3.address)))
    scenario.verify(~representatives.has_voted(sp.record(proposal_id=0, user=user4.address)))
    scenario.verify(representatives.data.proposals[0].positive_votes == 2)
    scenario.verify(~representatives.data.proposals[0].executed)

    # The second user changes their vote
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)

    # Check that the votes have been updated
    scenario.verify(representatives.data.votes[(0, user2.address)] == False)
    scenario.verify(representatives.data.proposals[0].positive_votes == 1)

    # The third user also changes their vote
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)

    # Check that the votes have been updated
    scenario.verify(representatives.data.votes[(0, user3.address)] == True)
    scenario.verify(representatives.data.proposals[0].positive_votes == 2)

    # Check that voting twice positive only counts as one vote
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario.verify(representatives.data.proposals[0].positive_votes == 2)

    # Check that voting twice negative doesn't modify the result
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario.verify(representatives.data.proposals[0].positive_votes == 2)

    # Check that the proposal cannot be executed because it doesn't have enough positive votes
    representatives.execute_proposal(0).run(valid=False, sender=user1)

    # The 4th user votes positive
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Check that the vote has been added
    scenario.verify(representatives.has_voted(sp.record(proposal_id=0, user=user4.address)))
    scenario.verify(representatives.data.votes[(0, user4.address)] == True)
    scenario.verify(representatives.data.proposals[0].positive_votes == 3)
    scenario.verify(~representatives.data.proposals[0].executed)

    # Check that the proposal can only be executed by one of the users
    representatives.execute_proposal(0).run(valid=False, sender=non_user)

    # Execute the proposal with one of the users
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(representatives.data.proposals[0].executed)
    scenario.verify(representatives.get_proposal(0).executed)

    # Check that the proposal cannot be voted or executed anymore
    representatives.vote_proposal(proposal_id=0, approval=True).run(valid=False, sender=user1)
    representatives.execute_proposal(0).run(valid=False, sender=user1)

    # Check that the new user can create a new proposal and vote it
    representatives.remove_user_proposal(user1.address).run(sender=non_user, now=sp.timestamp(0))
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=non_user, now=sp.timestamp(1000))

    # Check that the proposal and vote have been added to the big maps
    scenario.verify(representatives.data.proposals.contains(1))
    scenario.verify(representatives.data.counter == 2)
    scenario.verify(representatives.get_proposal_count() == 2)
    scenario.verify(representatives.data.proposals[1].positive_votes == 1)
    scenario.verify(representatives.get_proposal(1).positive_votes == 1)
    scenario.verify(~representatives.data.proposals[1].executed)
    scenario.verify(~representatives.get_proposal(1).executed)
    scenario.verify(representatives.get_vote(sp.record(proposal_id=1, user=non_user.address)) == True)
    scenario.verify(representatives.has_voted(sp.record(proposal_id=1, user=non_user.address)))

    # The other users vote the proposal
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user1, now=sp.timestamp(2000))
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user2, now=sp.timestamp(3000))
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user3, now=sp.timestamp(4000))
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user4, now=sp.timestamp(0).add_days(3))

    # Check that is not possible to vote or execute the proposal when it has expired
    representatives.vote_proposal(proposal_id=1, approval=False).run(valid=False, sender=user1, now=sp.timestamp(1).add_days(3))
    representatives.execute_proposal(1).run(valid=False, sender=user1, now=sp.timestamp(100).add_days(3))


@sp.add_test(name="Test text proposal")
def test_text_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Add a text proposal
    text = sp.pack("ipfs://zzz")
    representatives.text_proposal(text).run(sender=user1)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(representatives.data.proposals[0].executed)


@sp.add_test(name="Test transter mutez proposal")
def test_transfer_mutez_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Create the accounts that will receive the tez transfers and add the to
    # the scenario
    recipient1 = Recipient()
    recipient2 = Recipient()
    scenario += recipient1
    scenario += recipient2

    # Add a transfer tez proposal
    mutez_transfers = sp.list([
        sp.record(amount=sp.tez(3), destination=recipient1.address),
        sp.record(amount=sp.tez(2), destination=recipient2.address)])
    representatives.transfer_mutez_proposal(mutez_transfers).run(sender=user1)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(representatives.data.proposals[0].executed)

    # Check that the contract balance is correct
    scenario.verify(representatives.balance == sp.tez(10 - 3 - 2))

    # Check that the tez amounts have been sent to the correct destinations
    scenario.verify(recipient1.balance == sp.tez(3))
    scenario.verify(recipient2.balance == sp.tez(2))


@sp.add_test(name="Test transter token proposal")
def test_transfer_token_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Create the FA2 token contract and add it to the test scenario
    admin = sp.test_account("admin")
    fa2 = fa2Module.FA2(
        config=fa2Module.FA2_config(),
        admin=admin.address,
        meta=sp.utils.metadata_of_url("ipfs://aaa"))
    scenario += fa2

    # Mint one token
    fa2.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        token_info={"" : sp.utils.bytes_of_string("ipfs://bbb")}).run(sender=admin)

    # The first user transfers 20 editions of the token to the representatives
    fa2.transfer(sp.list([sp.record(
        from_=user1.address,
        txs=sp.list([sp.record(
            to_=representatives.address,
            token_id=0,
            amount=20)]))])).run(sender=user1)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 100 - 20)
    scenario.verify(fa2.data.ledger[(representatives.address, 0)].balance == 20)

    # Create the accounts that will receive the token transfers
    receptor1 = sp.test_account("receptor1")
    receptor2 = sp.test_account("receptor2")

    # Add a transfer token proposal
    token_transfers = sp.record(
        fa2=fa2.address,
        token_id=sp.nat(0),
        distribution=sp.list([
            sp.record(amount=sp.nat(5), destination=receptor1.address),
            sp.record(amount=sp.nat(1), destination=receptor2.address)]))
    representatives.transfer_token_proposal(token_transfers).run(sender=user3)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(representatives.data.proposals[0].executed)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 100 - 20)
    scenario.verify(fa2.data.ledger[(representatives.address, 0)].balance == 20 - 5 - 1)
    scenario.verify(fa2.data.ledger[(receptor1.address, 0)].balance == 5)
    scenario.verify(fa2.data.ledger[(receptor2.address, 0)].balance == 1)


@sp.add_test(name="Test minimum votes proposal")
def test_minimum_votes_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Check that the minimum votes cannot be set to 0
    representatives.minimum_votes_proposal(0).run(valid=False, sender=user4)

    # Add a minimum votes proposal
    representatives.minimum_votes_proposal(4).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the minimum votes parameter has been updated
    scenario.verify(representatives.data.minimum_votes == 4)
    scenario.verify(representatives.get_minimum_votes() == 4)

    # Propose a minimum votes proposal larger than the number of users
    representatives.minimum_votes_proposal(10).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=1, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=1, approval=True).run(sender=user4)

    # Check that the proposal can't be executed because the number of users is smaller
    # than the proposed minimum votes
    representatives.execute_proposal(1).run(valid=False, sender=user3)

    # Add a remove user proposal
    representatives.remove_user_proposal(user1.address).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=2, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=2, approval=True).run(sender=user2)
    representatives.vote_proposal(proposal_id=2, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=2, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(2).run(sender=user3)

    # Check that the minimum votes parameter has been updated
    scenario.verify(representatives.data.minimum_votes == 3)
    scenario.verify(representatives.get_minimum_votes() == 3)


@sp.add_test(name="Test expiration time proposal")
def test_expiration_time_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Check that the expiration time cannot be set to 0
    representatives.expiration_time_proposal(0).run(valid=False, sender=user4)

    # Add an expiration time proposal
    representatives.expiration_time_proposal(100).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the expiration time parameter has been updated
    scenario.verify(representatives.data.expiration_time == 100)
    scenario.verify(representatives.get_expiration_time() == 100)


@sp.add_test(name="Test add user proposal")
def test_add_user_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Create the new user account
    user5 = sp.test_account("user5")

    # Check that it's not possible to add the same user twice
    representatives.add_user_proposal(user1.address).run(valid=False, sender=user4)

    # Add a add user proposal
    representatives.add_user_proposal(user5.address).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that now there are 5 users
    scenario.verify(sp.len(representatives.data.users.elements()) == 5)
    scenario.verify(sp.len(representatives.get_users().elements()) == 5)
    scenario.verify(representatives.get_users().contains(user5.address))
    scenario.verify(representatives.is_user(user5.address))


@sp.add_test(name="Test remove user proposal")
def test_remove_user_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Create the new user account
    user5 = sp.test_account("user5")

    # Check that it's not possible to remove a user that is not in the representatives
    representatives.remove_user_proposal(user5.address).run(valid=False, sender=user4)

    # Add a remove user proposal
    representatives.remove_user_proposal(user2.address).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that now there are 3 users
    scenario.verify(sp.len(representatives.data.users.elements()) == 3)
    scenario.verify(sp.len(representatives.get_users().elements()) == 3)
    scenario.verify(~representatives.get_users().contains(user2.address))
    scenario.verify(~representatives.is_user(user2.address))


@sp.add_test(name="Test lambda function proposal")
def test_lambda_function_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    representatives = testEnvironment["representatives"]

    # Initialize the dummy contract and add it to the test scenario
    dummyContract = Dummy()
    scenario += dummyContract

    # Define the lambda function that will update the dummy contract
    def dummy_lambda_function(params):
        sp.set_type(params, sp.TUnit)
        dummyContractHandle = sp.contract(sp.TNat, dummyContract.address, "update_x").open_some()
        sp.result([sp.transfer_operation(sp.nat(2), sp.mutez(0), dummyContractHandle)])

    # Add a lambda proposal
    representatives.lambda_function_proposal(dummy_lambda_function).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the dummy contract storage has been updated to the correct vale
    scenario.verify(dummyContract.data.x == 2)
    scenario.verify(dummyContract.data.y == 0)


@sp.add_test(name="Test set dao")
def test_set_dao():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    dao = testEnvironment["dao"]
    representatives = testEnvironment["representatives"]

    # Create a new DAO test account
    new_dao = sp.test_account("new_dao")

    # Define the lambda function that will set the new DAO address
    def dao_lambda_function(params):
        sp.set_type(params, sp.TUnit)
        set_dao_handle = sp.contract(sp.TAddress, representatives.address, "set_dao").open_some()
        sp.result([sp.transfer_operation(new_dao.address, sp.mutez(0), set_dao_handle)])

    # Check the initial DAO address
    scenario.verify(representatives.data.dao == dao.address)

    # Add a lambda proposal
    representatives.lambda_function_proposal(dao_lambda_function).run(sender=user4)

    # Vote for the proposal
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    representatives.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    representatives.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    representatives.execute_proposal(0).run(sender=user3)

    # Check that the DAO address has been updated
    scenario.verify(representatives.data.dao == new_dao.address)
