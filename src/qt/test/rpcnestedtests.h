// Copyright (c) 2016 The Bitcoin Core developers
// Copyright (c) 2016-2019 The MagnaChain Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef MAGNACHAIN_QT_TEST_RPC_NESTED_TESTS_H
#define MAGNACHAIN_QT_TEST_RPC_NESTED_TESTS_H

#include <QObject>
#include <QTest>

#include "transaction/txdb.h"
#include "transaction/txmempool.h"

class RPCNestedTests : public QObject
{
    Q_OBJECT

    private Q_SLOTS:
    void rpcNestedTests();

private:
    MCCoinsViewDB *pcoinsdbview;
};

#endif // MAGNACHAIN_QT_TEST_RPC_NESTED_TESTS_H
