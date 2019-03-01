#!/usr/bin/env python3
# Copyright (c) 2014-2016 The MagnaChain Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Helpful routines for regression testing."""

from base64 import b64encode
from binascii import hexlify, unhexlify
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
import logging
import os
import random
import re
from subprocess import CalledProcessError
import time

from . import coverage
from .authproxy import AuthServiceProxy, JSONRPCException

logger = logging.getLogger("TestFramework.utils")

# Assert functions
##################

def assert_contains(string,sub_string):
    if sub_string not in string:
        raise AssertionError("(%s) not in (%s)" %(sub_string,string))



def assert_fee_amount(fee, tx_size, fee_per_kB):
    """Assert the fee was in range"""
    target_fee = tx_size * fee_per_kB / 1000
    if fee < target_fee:
        raise AssertionError("Fee of %s MGC too low! (Should be %s MGC)" % (str(fee), str(target_fee)))
    # allow the wallet's estimation to be at most 2 bytes off
    if fee > (tx_size + 2) * fee_per_kB / 1000:
        raise AssertionError("Fee of %s MGC too high! (Should be %s MGC)" % (str(fee), str(target_fee)))

def assert_equal(thing1, thing2, *args):
    if thing1 != thing2 or any(thing1 != arg for arg in args):
        raise AssertionError("not(%s)" % " == ".join(str(arg) for arg in (thing1, thing2) + args))

def assert_greater_than(thing1, thing2):
    if thing1 <= thing2:
        raise AssertionError("%s <= %s" % (str(thing1), str(thing2)))

def assert_greater_than_or_equal(thing1, thing2):
    if thing1 < thing2:
        raise AssertionError("%s < %s" % (str(thing1), str(thing2)))

def assert_raises(exc, fun, *args, **kwds):
    assert_raises_message(exc, None, fun, *args, **kwds)

def assert_raises_message(exc, message, fun, *args, **kwds):
    try:
        fun(*args, **kwds)
    except JSONRPCException:
        raise AssertionError("Use assert_raises_rpc_error() to test RPC failures")
    except exc as e:
        if message is not None and message not in e.error['message']:
            raise AssertionError("Expected substring not found:" + e.error['message'])
    except Exception as e:
        raise AssertionError("Unexpected exception raised: " + type(e).__name__)
    else:
        raise AssertionError("No exception raised")

def assert_raises_process_error(returncode, output, fun, *args, **kwds):
    """Execute a process and asserts the process return code and output.

    Calls function `fun` with arguments `args` and `kwds`. Catches a CalledProcessError
    and verifies that the return code and output are as expected. Throws AssertionError if
    no CalledProcessError was raised or if the return code and output are not as expected.

    Args:
        returncode (int): the process return code.
        output (string): [a substring of] the process output.
        fun (function): the function to call. This should execute a process.
        args*: positional arguments for the function.
        kwds**: named arguments for the function.
    """
    try:
        fun(*args, **kwds)
    except CalledProcessError as e:
        if returncode != e.returncode:
            raise AssertionError("Unexpected returncode %i" % e.returncode)
        if output not in e.output:
            raise AssertionError("Expected substring not found:" + e.output)
    else:
        raise AssertionError("No exception raised")

def assert_raises_rpc_error(code, message, fun, *args, **kwds):
    """Run an RPC and verify that a specific JSONRPC exception code and message is raised.

    Calls function `fun` with arguments `args` and `kwds`. Catches a JSONRPCException
    and verifies that the error code and message are as expected. Throws AssertionError if
    no JSONRPCException was raised or if the error code/message are not as expected.

    Args:
        code (int), optional: the error code returned by the RPC call (defined
            in src/rpc/protocol.h). Set to None if checking the error code is not required.
        message (string), optional: [a substring of] the error string returned by the
            RPC call. Set to None if checking the error string is not required.
        fun (function): the function to call. This should be the name of an RPC.
        args*: positional arguments for the function.
        kwds**: named arguments for the function.
    """
    assert try_rpc(code, message, fun, *args, **kwds), "No exception raised"

def try_rpc(code, message, fun, *args, **kwds):
    """Tries to run an rpc command.

    Test against error code and message if the rpc fails.
    Returns whether a JSONRPCException was raised."""
    try:
        fun(*args, **kwds)
    except JSONRPCException as e:
        # JSONRPCException was thrown as expected. Check the code and message values are correct.
        if (code is not None) and (code != e.error["code"]):
            raise AssertionError("Unexpected JSONRPC error code %i" % e.error["code"])
        if (message is not None) and (message not in e.error['message']):
            raise AssertionError("Expected substring not found:" + e.error['message'])
        return True
    except Exception as e:
        raise AssertionError("Unexpected exception raised: " + type(e).__name__)
    else:
        return False

def assert_is_hex_string(string):
    try:
        int(string, 16)
    except Exception as e:
        raise AssertionError(
            "Couldn't interpret %r as hexadecimal; raised: %s" % (string, e))

def assert_is_hash_string(string, length=64):
    if not isinstance(string, str):
        raise AssertionError("Expected a string, got type %r" % type(string))
    elif length and len(string) != length:
        raise AssertionError(
            "String of length %d expected; got %d" % (length, len(string)))
    elif not re.match('[abcdef0-9]+$', string):
        raise AssertionError(
            "String %r contains invalid characters for a hash." % string)

def assert_array_result(object_array, to_match, expected, should_not_find=False):
    """
        Pass in array of JSON objects, a dictionary with key/value pairs
        to match against, and another dictionary with expected key/value
        pairs.
        If the should_not_find flag is true, to_match should not be found
        in object_array
        """
    if should_not_find:
        assert_equal(expected, {})
    num_matched = 0
    for item in object_array:
        all_match = True
        for key, value in to_match.items():
            if item[key] != value:
                all_match = False
        if not all_match:
            continue
        elif should_not_find:
            num_matched = num_matched + 1
        for key, value in expected.items():
            if item[key] != value:
                raise AssertionError("%s : expected %s=%s" % (str(item), str(key), str(value)))
            num_matched = num_matched + 1
    if num_matched == 0 and not should_not_find:
        raise AssertionError("No objects matched %s" % (str(to_match)))
    if num_matched > 0 and should_not_find:
        raise AssertionError("Objects were found %s" % (str(to_match)))

# Utility functions
###################

def check_json_precision():
    """Make sure json library being used does not lose precision converting BTC values"""
    n = Decimal("20000000.00000003")
    satoshis = int(json.loads(json.dumps(float(n))) * 1.0e8)
    if satoshis != 2000000000000003:
        raise RuntimeError("JSON encode/decode loses precision")

def count_bytes(hex_string):
    return len(bytearray.fromhex(hex_string))

def bytes_to_hex_str(byte_str):
    return hexlify(byte_str).decode('ascii')

def hash256(byte_str):
    sha256 = hashlib.sha256()
    sha256.update(byte_str)
    sha256d = hashlib.sha256()
    sha256d.update(sha256.digest())
    return sha256d.digest()[::-1]

def hex_str_to_bytes(hex_str):
    return unhexlify(hex_str.encode('ascii'))

def str_to_b64str(string):
    return b64encode(string.encode('utf-8')).decode('ascii')

def satoshi_round(amount):
    return Decimal(amount).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

def wait_until(predicate, *, attempts=float('inf'), timeout=float('inf'), lock=None):
    if attempts == float('inf') and timeout == float('inf'):
        timeout = 60
    attempt = 0
    timeout += time.time()

    while attempt < attempts and time.time() < timeout:
        if lock:
            with lock:
                if predicate():
                    return
        else:
            if predicate():
                return
        attempt += 1
        time.sleep(0.05)

    # Print the cause of the timeout
    assert_greater_than(attempts, attempt)
    assert_greater_than(timeout, time.time())
    raise RuntimeError('Unreachable')

# RPC/P2P connection constants and functions
############################################

# The maximum number of nodes a single test can spawn
MAX_NODES = 8
# Don't assign rpc or p2p ports lower than this
PORT_MIN = 11000
# The number of ports to "reserve" for p2p and rpc, each
PORT_RANGE = 5000

class PortSeed:
    # Must be initialized with a unique integer for each process
    n = None

def get_rpc_proxy(url, node_number, timeout=None, coveragedir=None):
    """
    Args:
        url (str): URL of the RPC server to call
        node_number (int): the node number (or id) that this calls to

    Kwargs:
        timeout (int): HTTP timeout in seconds

    Returns:
        AuthServiceProxy. convenience object for making RPC calls.

    """
    proxy_kwargs = {}
    if timeout is not None:
        proxy_kwargs['timeout'] = timeout

    proxy = AuthServiceProxy(url, **proxy_kwargs)
    proxy.url = url  # store URL on proxy for info

    coverage_logfile = coverage.get_filename(
        coveragedir, node_number) if coveragedir else None

    return coverage.AuthServiceProxyWrapper(proxy, coverage_logfile)

def p2p_port(n):
    assert(n <= MAX_NODES)
    return PORT_MIN + n + (MAX_NODES * PortSeed.n) % (PORT_RANGE - 1 - MAX_NODES)

def rpc_port(n):
    return PORT_MIN + PORT_RANGE + n + (MAX_NODES * PortSeed.n) % (PORT_RANGE - 1 - MAX_NODES)

def rpc_url(datadir, i, rpchost=None):
    rpc_u, rpc_p = get_auth_cookie(datadir)
    host = '127.0.0.1'
    port = rpc_port(i)
    if rpchost:
        parts = rpchost.split(':')
        if len(parts) == 2:
            host, port = parts
        else:
            host = rpchost
    return "http://%s:%s@%s:%d" % (rpc_u, rpc_p, host, int(port))

# Node functions
################

def initialize_datadir(dirname, n):
    datadir = os.path.join(dirname, "node" + str(n))
    if not os.path.isdir(datadir):
        os.makedirs(datadir)
    with open(os.path.join(datadir, "magnachain.conf"), 'w', encoding='utf8') as f:
        f.write("regtest=1\n")
        f.write("port=" + str(p2p_port(n)) + "\n")
        f.write("rpcport=" + str(rpc_port(n)) + "\n")
        f.write("listenonion=0\n")
    return datadir

def get_datadir_path(dirname, n):
    return os.path.join(dirname, "node" + str(n))

def get_auth_cookie(datadir):
    user = None
    password = None
    if os.path.isfile(os.path.join(datadir, "magnachain.conf")):
        with open(os.path.join(datadir, "magnachain.conf"), 'r', encoding='utf8') as f:
            for line in f:
                if line.startswith("rpcuser="):
                    assert user is None  # Ensure that there is only one rpcuser line
                    user = line.split("=")[1].strip("\n")
                if line.startswith("rpcpassword="):
                    assert password is None  # Ensure that there is only one rpcpassword line
                    password = line.split("=")[1].strip("\n")
    if os.path.isfile(os.path.join(datadir, "regtest", ".cookie")):
        with open(os.path.join(datadir, "regtest", ".cookie"), 'r') as f:
            userpass = f.read()
            split_userpass = userpass.split(':')
            user = split_userpass[0]
            password = split_userpass[1]
    if user is None or password is None:
        raise ValueError("No RPC credentials")
    return user, password

def log_filename(dirname, n_node, logname):
    return os.path.join(dirname, "node" + str(n_node), "regtest", logname)

def get_bip9_status(node, key):
    info = node.getblockchaininfo()
    return info['bip9_softforks'][key]

def set_node_times(nodes, t):
    for node in nodes:
        node.setmocktime(t)

def disconnect_nodes(from_connection, node_num):
    for peer_id in [peer['id'] for peer in from_connection.getpeerinfo() if "testnode%d" % node_num in peer['subver']]:
        from_connection.disconnectnode(nodeid=peer_id)

    for _ in range(50):
        if [peer['id'] for peer in from_connection.getpeerinfo() if "testnode%d" % node_num in peer['subver']] == []:
            break
        time.sleep(0.1)
    else:
        raise AssertionError("timed out waiting for disconnect")

def connect_nodes(from_connection, node_num):
    ip_port = "127.0.0.1:" + str(p2p_port(node_num))
    from_connection.addnode(ip_port, "onetry")
    # poll until version handshake complete to avoid race conditions
    # with transaction relaying
    while any(peer['version'] == 0 for peer in from_connection.getpeerinfo()):
        time.sleep(0.1)

def connect_nodes_bi(nodes, a, b):
    connect_nodes(nodes[a], b)
    connect_nodes(nodes[b], a)

def sync_blocks(rpc_connections, *, wait=1, timeout=60, logger=None):
    """
    Wait until everybody has the same tip.

    sync_blocks needs to be called with an rpc_connections set that has least
    one node already synced to the latest, stable tip, otherwise there's a
    chance it might return before all nodes are stably synced.
    """
    # Use getblockcount() instead of waitforblockheight() to determine the
    # initial max height because the two RPCs look at different internal global
    # variables (chainActive vs latestBlock) and the former gets updated
    # earlier.
    maxheight = max(x.getblockcount() for x in rpc_connections)
    if logger:
        logger.info("maxheight: " + str(maxheight))
    start_time = cur_time = time.time()
    while cur_time <= start_time + timeout:
        tips = [r.waitforblockheight(maxheight, int(wait * 1000)) for r in rpc_connections]
        if all(t["height"] == maxheight for t in tips):
            if all(t["hash"] == tips[0]["hash"] for t in tips):
                return
            raise AssertionError("Block sync failed, mismatched block hashes:{}".format(
                                 "".join("\n  {!r}".format(tip) for tip in tips)))
        cur_time = time.time()
    raise AssertionError("Block sync to height {} timed out:{}".format(
                         maxheight, "".join("\n  {!r}".format(tip) for tip in tips)))

def sync_chain(rpc_connections, *, wait=1, timeout=60):
    """
    Wait until everybody has the same best block
    """
    while timeout > 0:
        best_hash = [x.getbestblockhash() for x in rpc_connections]
        if best_hash == [best_hash[0]] * len(best_hash):
            return
        time.sleep(wait)
        timeout -= wait
    raise AssertionError("Chain sync failed: Best block hashes don't match")

def sync_mempools(rpc_connections, *, wait=1, timeout=60):
    """
    Wait until everybody has the same transactions in their memory
    pools
    """
    while timeout > 0:
        pool = set(rpc_connections[0].getrawmempool())
        num_match = 1
        for i in range(1, len(rpc_connections)):
            if set(rpc_connections[i].getrawmempool()) == pool:
                num_match = num_match + 1
        if num_match == len(rpc_connections):
            return
        time.sleep(wait)
        timeout -= wait
    raise AssertionError("Mempool sync failed")

# Transaction/Block functions
#############################

def find_output(node, txid, amount):
    """
    Return index to output of txid with value amount
    Raises exception if there is none.
    """
    txdata = node.getrawtransaction(txid, 1)
    for i in range(len(txdata["vout"])):
        if txdata["vout"][i]["value"] == amount:
            return i
    raise RuntimeError("find_output txid %s : %s not found" % (txid, str(amount)))

def gather_inputs(from_node, amount_needed, confirmations_required=1):
    """
    Return a random set of unspent txouts that are enough to pay amount_needed
    """
    assert(confirmations_required >= 0)
    utxo = from_node.listunspent(confirmations_required)
    random.shuffle(utxo)
    inputs = []
    total_in = Decimal("0.00000000")
    while total_in < amount_needed and len(utxo) > 0:
        t = utxo.pop()
        total_in += t["amount"]
        inputs.append({"txid": t["txid"], "vout": t["vout"], "address": t["address"]})
    if total_in < amount_needed:
        raise RuntimeError("Insufficient funds: need %d, have %d" % (amount_needed, total_in))
    return (total_in, inputs)

def make_change(from_node, amount_in, amount_out, fee):
    """
    Create change output(s), return them
    """
    outputs = {}
    amount = amount_out + fee
    change = amount_in - amount
    if change > amount * 2:
        # Create an extra change output to break up big inputs
        change_address = from_node.getnewaddress()
        # Split change in two, being careful of rounding:
        outputs[change_address] = Decimal(change / 2).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        change = amount_in - amount - outputs[change_address]
    if change > 0:
        outputs[from_node.getnewaddress()] = change
    return outputs

def random_transaction(nodes, amount, min_fee, fee_increment, fee_variants):
    """
    Create a random transaction.
    Returns (txid, hex-encoded-transaction-data, fee)
    """
    from_node = random.choice(nodes)
    to_node = random.choice(nodes)
    fee = min_fee + fee_increment * random.randint(0, fee_variants)

    (total_in, inputs) = gather_inputs(from_node, amount + fee)
    outputs = make_change(from_node, total_in, amount, fee)
    outputs[to_node.getnewaddress()] = float(amount)

    rawtx = from_node.createrawtransaction(inputs, outputs)
    signresult = from_node.signrawtransaction(rawtx)
    txid = from_node.sendrawtransaction(signresult["hex"], True)

    return (txid, signresult["hex"], fee)

# Helper to create at least "count" utxos
# Pass in a fee that is sufficient for relay and mining new transactions.
def create_confirmed_utxos(fee, node, count):
    # to_generate = int(0.5 * count) + 101
    to_generate = int(0.5 * count) + 2
    while to_generate > 0:
        node.generate(min(25, to_generate))
        to_generate -= 25
    utxos = node.listunspent()
    iterations = count - len(utxos)
    addr1 = node.getnewaddress()
    addr2 = node.getnewaddress()
    if iterations <= 0:
        return utxos
    for i in range(iterations):
        t = utxos.pop()
        inputs = []
        inputs.append({"txid": t["txid"], "vout": t["vout"]})
        outputs = {}
        send_value = t['amount'] - fee
        outputs[addr1] = satoshi_round(send_value / 2)
        outputs[addr2] = satoshi_round(send_value / 2)
        raw_tx = node.createrawtransaction(inputs, outputs)
        signed_tx = node.signrawtransaction(raw_tx)["hex"]
        node.sendrawtransaction(signed_tx)

    while (node.getmempoolinfo()['size'] > 0):
        node.generate(1)

    utxos = node.listunspent()
    assert(len(utxos) >= count)
    return utxos

# Create large OP_RETURN txouts that can be appended to a transaction
# to make it large (helper for constructing large transactions).
def gen_return_txouts():
    # Some pre-processing to create a bunch of OP_RETURN txouts to insert into transactions we create
    # So we have big transactions (and therefore can't fit very many into each block)
    # create one script_pubkey
    script_pubkey = "6a4d0200"  # OP_RETURN OP_PUSH2 512 bytes
    for i in range(512):
        script_pubkey = script_pubkey + "01"
    # concatenate 128 txouts of above script_pubkey which we'll insert before the txout for change
    txouts = "81"
    for k in range(128):
        # add txout value
        txouts = txouts + "0000000000000000"
        # add length of script_pubkey
        txouts = txouts + "fd0402"
        # add script_pubkey
        txouts = txouts + script_pubkey
    return txouts

def create_tx(node, coinbase, to_address, amount):
    inputs = [{"txid": coinbase, "vout": 0}]
    outputs = {to_address: amount}
    rawtx = node.createrawtransaction(inputs, outputs)
    signresult = node.signrawtransaction(rawtx)
    assert_equal(signresult["complete"], True)
    return signresult["hex"]

# Create a spend of each passed-in utxo, splicing in "txouts" to each raw
# transaction to make it large.  See gen_return_txouts() above.
def create_lots_of_big_transactions(node, txouts, utxos, num, fee):
    addr = node.getnewaddress()
    txids = []
    for _ in range(num):
        t = utxos.pop()
        inputs = [{"txid": t["txid"], "vout": t["vout"]}]
        outputs = {}
        change = t['amount'] - fee
        outputs[addr] = satoshi_round(change)
        rawtx = node.createrawtransaction(inputs, outputs)
        newtx = rawtx[0:92]
        newtx = newtx + txouts
        newtx = newtx + rawtx[94:]
        signresult = node.signrawtransaction(newtx, None, None, "NONE")
        txid = node.sendrawtransaction(signresult["hex"], True)
        txids.append(txid)
    return txids

def mine_large_block(node, utxos=None):
    # generate a 66k transaction,
    # and 14 of them is close to the 1MB block limit
    num = 14
    txouts = gen_return_txouts()
    utxos = utxos if utxos is not None else []
    if len(utxos) < num:
        utxos.clear()
        utxos.extend(node.listunspent())
    fee = 100 * node.getnetworkinfo()["relayfee"]
    create_lots_of_big_transactions(node, txouts, utxos, num, fee=fee)
    node.generate(1)

def mine_large_block_with_mocktime(node, utxos=None,mocktime = None):
    # generate a 66k transaction,
    # and 14 of them is close to the 1MB block limit
    num = 14
    txouts = gen_return_txouts()
    utxos = utxos if utxos is not None else []
    if len(utxos) < num:
        utxos.clear()
        utxos.extend(node.listunspent())
    fee = 100 * node.getnetworkinfo()["relayfee"]
    create_lots_of_big_transactions(node, txouts, utxos, num, fee=fee)
    print("mocktime:",mocktime)
    node.setmocktime(mocktime)
    node.generate(1)



###############################
# smart contract functools
def generate_contract(folder, err_type=None):
    '''
    生成合约代码
    :param dir:
    :return:
    '''
    code = '''
        cell = 100000000
        
        function say( ... )
            -- body
            if _G.print then
                print(...)
            else
            end
        end


        function tailLoopTest(start)
            if start < 0 then
                return 0
            else
                --say("start is " ,tostring(start))
                return tailLoopTest(start - 1)
            end
        end

        function lotsOfParamsTest(p1, p2, p3, p4, p5, p6, p7, p8, p9, p10,
                   p11, p12, p13, p14, p15, p16, p17, p18, p19, p20,
                   p21, p22, p23, p24, p25, p26, p27, p28, p29, p30,
                   p31, p32, p33, p34, p35, p36, p37, p38, p39, p40,
                   p41, p42, p43, p44, p45, p46, p48, p49, p50, p51,...)
          local a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14
          --say("test lots of params with func")
        end



        function tailLoopTest2(i, ...)
          if i == 0 then
            return ...
          else
            return tailLoopTest2(i-1, 1, ...)
          end
        end

        function unpackTest( ... )
            -- body
            unpack({}, 0, 2^31 - 1)
        end
        
        local function _call(addr,f,...)
            say("call:",addr,f,...)
            --showMsg()
            say(callcontract(addr,f,...))
        end

        function mainTest()
            --say("begin test")
            lotsOfParamsTest()
            tailLoopTest(32)
            --say('n pack test end')
            local mt = {}
            mt.__newindex = mt
            local t = setmetatable({}, mt)
            t[1] = 1
            t[2^31] = 2
            --say("big table test")
            --unpackTest()
            --say('unpack test ok')
        end

        local function _private( ... )
            -- body
        end

        function localFuncTest( ... )
            -- body
            _call(msg.thisaddress,"_private")
        end

        function showMsg()
            for k,v in pairs(msg) do
                say(k," ---> ",v)
            end
        end

        function callOtherContractTest(addr,func,...)
            say("beCall by ",senderType , ",address is " , msg.sender )
            --addr = msg.thisaddress
            _call(addr,func,...)
            sendCoinTest(msg.origin,10)
        end

        function contractDataTest( ... )
            -- body
            PersistentData.size = PersistentData.size - 1
            PersistentData.negative = PersistentData.negative -1
            PersistentData.counter = PersistentData.counter + 1
            PersistentData[tostring(PersistentData.counter ^ 512 - 1)] = (PersistentData.counter ^ 512 - 1)
            --PersistentData[table.concat( {'field', tostring(PersistentData.counter ^ 512 - 1)},"")] = (PersistentData.counter ^ 512 - 1)
            --[[
            for k,v in pairs(PersistentData) do
                say(k,v)
            end
            --]]
        end

        function sendCoinTest( to,inum )
            -- body
            cell = 100000000
            inum = inum or 1
            ret = send(to,inum * cell)
            --say("send ret:",ret)
        end

        function sendCoinTest2( to )
            -- body
            ret = send(to,100000)
        end
        
        function dustChangeTest(to)
            -- body
            --dust to this contract
            cell = 100000000
            ret = send(to,cell - 999)
            say("dustChangeTest ret:",ret)
        end
        
        function addWithdrawList( ... )
            -- body
            for _,v in ipairs({...}) do
                table.insert(PersistentData.withdrawList,v)
            end
        end

        function batchSendTest()
            -- body
            cell = 100000000
            ret = false
            for _,to in pairs(PersistentData.withdrawList) do
                ret = send(to,1 * cell)
            end
            return ret
        end

        function setThirdPartyContract( ... )
            -- body
            for i,v in ipairs({ ... }) do
                table.insert(PersistentData.thirdPartyContracts,v)
            end
        end


        glob = 10
        function setGlob(val)
            say('before set:',glob)
            glob = val
            PersistentData.decimals = val
            say('after set:',glob)
        end

        function maxContractCallTest(inum)
            _call(msg.thisaddress,'setGlob',100)
            for i=1,inum do
                _call(msg.thisaddress,'setGlob',100)
            end
        end
        
        function reentrancyTest( to )
            -- body
            _call(msg.thisaddress,'updateContract','this','')
            _call(msg.thisaddress,'cycleSelf')
            _call(msg.thisaddress,'updateContract','this','')
            _call(msg.thisaddress,'cycleSelf')
            
        end

        function rpcSendTest()
            -- body
            _call(msg.thisaddress,'send',msg.sender,10)
        end

        function doubleSpendTest(to)
            -- body
            t={a=1121212,c=121212,b=3,d=4,e=5,f=6,g=7,h=8,i=9,a0 = 12,243546,565,6,6,}
            last = -1
            for i=1,10 do
                j = 0
                for k,v in pairs(t) do
                    if k == 'b' then
                        if last ~= -1 and last ~= j then
                            --may be doubleSpend here
                            if j % 2 == 0 then
                                send(to,1 * cell)
                            else
                                send(msg.sender,1 * cell)
                            end
                            last = j
                        end
                        if last == -1 then
                            last = j
                        end
                    end
                    j = j + 1
                end
                index = {1,2,3}
                t[tostring(i)] = index
                table.insert(t,i)
            end
        end

        function cmsgpackTest( ... )
            -- body
            PersistentData["this"] = PersistentData
            PersistentData["this1"] = PersistentData
            PersistentData["this2"] = PersistentData
        end        
        
        function reorgTest(to)
            if msg.timestamp % 2 == 0 then
                send(to,1 * cell)
            else
                send(msg.origin,1 * cell)
            end
        end
        
        function init()
            mainTest()
            PersistentData = {}
            PersistentData.name = "RMB"
            PersistentData.symbol = "$" --token symbol
            PersistentData.decimals = 0 --
            PersistentData.decimalsNum = math.pow(10, PersistentData.decimals)
            local initialSupply = 21000000
            PersistentData.totalSupply = initialSupply * PersistentData.decimalsNum
            PersistentData.balanceOf = {}
            PersistentData.balanceOf[msg.sender] = PersistentData.totalSupply
            PersistentData.counter = 1
            PersistentData.thirdPartyContracts = {}
            PersistentData.size = 128
            PersistentData.negative = 0
            PersistentData.withdrawList = {}
            setUpHook()
            PersistentData.func = function ( ... )
                -- body
                for k,v in pairs(PersistentData) do
                    say(k,v)
                end
            end
            if longReturnTest then
                return longReturnTest()
            end
        end


        function payable()
            --just for recharge
            str = [==[
            just for recharge
            ]==]
            return str
        end
        
        function get(key)
            -- body
            return PersistentData[key]
        end
        
        function updateContract( key,val )
            -- body
            PersistentData[key] = val
        end

        function cycleSelf()
            -- body
            --PersistentData["this"] = PersistentData
            PersistentData["this"] = {1,2,3,4,5,6,asd = {name = 'weigun',age = 18,7,8,9,infos={{1},{2},k = {n=true}}}}
        end
        
        function setUpHook()
            -- body
            setmetatable(_G,{__index = PersistentData})
        end
        
        function setNil( ... )
            -- body
            PersistentData = nil
        end  
    '''
    if err_type == "syntax_err":
        code += 'syntax_err'
    elif err_type == "bigfile":
        code += "local a = [==[\n" + "a" * (int(2147483647 / 30)) + "\n]==]"
    elif err_type == "trim_code":
        code += "--1" * 10
    elif err_type == "long_string_return":
        add_code = "function longReturnTest() return \"{}\" end\n".format('long long long ago ' * 2500)
        # add_code = "function longReturnTest() return {} '1' end\n".format("'string'," * 248)
        code += add_code
    file_path = os.path.join(folder, "contract.lua")
    with open(file_path, "w") as fh:
        fh.write(code)
    return file_path

def caller_factory(mgr,contract_id,sender):
    '''

    :param mgr: the test_framework obj
    :param contract_id:
    :param sender:
    :return: a function
    '''
    node = mgr.nodes[0]
    contract_id = contract_id
    sender = sender

    def _call_contract(func,*args,amount = random.randint(1, 10000),throw_exception = False):
        mgr.log.info("%s,%s,%s,%s,%s"%(contract_id,func,sender,amount,args))
        balance = node.getbalance()
        try:
            result = node.callcontract(True, amount, contract_id, sender, func,*args)
            mgr.log.info("beforecall balance:%s,aftercall balance:%s,in amount:%s,total cost :%s"%(balance,node.getbalance(),amount,balance - node.getbalance() - amount))
            return result
        except Exception as e:
            if throw_exception:
                raise
            print(e)
            assert all(re.findall('-\d\)$', repr(e)))
            return repr(e)
    return _call_contract


def gen_lots_of_contracts(node,contract,num = 500):
    """
    发布很多合约交易，用于构造需要大量合约交易的情况
    返回{txid:xxxxx,address:xxx}集合
    :param node:
    :param num:
    :return: txids
    """
    infos = []
    for i in range(num):
        result = node.publishcontract(contract)
        infos.append({'txid': result['txid'],'address' : result['contractaddress']})
    return infos

