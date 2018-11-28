// Copyright (c) 2016 The Bitcoin Core developers
// Copyright (c) 2016-2019 The MagnaChain Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "policy/rbf.h"

bool SignalsOptInRBF(const CellTransaction &tx)
{
    for (const CellTxIn &txin : tx.vin) {
        if (txin.nSequence < std::numeric_limits<unsigned int>::max()-1) {
            return true;
        }
    }
    return false;
}

RBFTransactionState IsRBFOptIn(const CellTransaction &tx, CellTxMemPool &pool)
{
    AssertLockHeld(pool.cs);

    CellTxMemPool::setEntries setAncestors;

    // First check the transaction itself.
    if (SignalsOptInRBF(tx)) {
        return RBF_TRANSACTIONSTATE_REPLACEABLE_BIP125;
    }

    // If this transaction is not in our mempool, then we can't be sure
    // we will know about all its inputs.
    if (!pool.exists(tx.GetHash())) {
        return RBF_TRANSACTIONSTATE_UNKNOWN;
    }

    // If all the inputs have nSequence >= maxint-1, it still might be
    // signaled for RBF if any unconfirmed parents have signaled.
    uint64_t noLimit = std::numeric_limits<uint64_t>::max();
    std::string dummy;
    CellTxMemPoolEntry entry = *pool.mapTx.find(tx.GetHash());
    pool.CalculateMemPoolAncestors(entry, setAncestors, noLimit, noLimit, noLimit, noLimit, dummy, false);

    for (CellTxMemPool::txiter it : setAncestors) {
        if (SignalsOptInRBF(it->GetTx())) {
            return RBF_TRANSACTIONSTATE_REPLACEABLE_BIP125;
        }
    }
    return RBF_TRANSACTIONSTATE_FINAL;
}
