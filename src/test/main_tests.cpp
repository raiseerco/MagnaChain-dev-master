// Copyright (c) 2014-2016 The Bitcoin Core developers
// Copyright (c) 2016-2019 The MagnaChain Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "chain/chainparams.h"
#include "validation/validation.h"
#include "net/net.h"

#ifdef BUILD_MSVC 
#define BOOST_TEST_MODULE maintest
#endif 

#include "test/test_magnachain.h"

#include <boost/signals2/signal.hpp>
#include <boost/test/unit_test.hpp>

BOOST_FIXTURE_TEST_SUITE(main_tests, TestingSetup)

static void TestBlockSubsidyHalvings(const Consensus::Params& consensusParams)
{
    int maxHalvings = 64;
    MCAmount nInitialSubsidy = 85 * COIN;

    MCAmount nPreviousSubsidy = nInitialSubsidy * 2; // for height == 0
    BOOST_CHECK_EQUAL(nPreviousSubsidy, nInitialSubsidy * 2);
    for (int nHalvings = 0; nHalvings < maxHalvings; nHalvings++) {
        int nHeight = nHalvings * consensusParams.nSubsidyHalvingInterval;
        MCAmount nSubsidy = GetBlockSubsidy(nHeight, consensusParams);
		if (consensusParams.BigBoomHeight >= nHeight)
		{
			BOOST_CHECK(nSubsidy <= nInitialSubsidy + consensusParams.BigBoomValue);
			BOOST_CHECK_EQUAL(nSubsidy, nPreviousSubsidy / 2 + consensusParams.BigBoomValue);
		}
		else
		{
			BOOST_CHECK(nSubsidy <= nInitialSubsidy);
			BOOST_CHECK_EQUAL(nSubsidy, nPreviousSubsidy / 2);
		}
        nPreviousSubsidy = nPreviousSubsidy / 2;//nSubsidy
    }
    BOOST_CHECK_EQUAL(GetBlockSubsidy(maxHalvings * consensusParams.nSubsidyHalvingInterval, consensusParams), 0);
}

static void TestBlockSubsidyHalvings(int nSubsidyHalvingInterval)
{
    Consensus::Params consensusParams;
    consensusParams.nSubsidyHalvingInterval = nSubsidyHalvingInterval;
    TestBlockSubsidyHalvings(consensusParams);
}

BOOST_AUTO_TEST_CASE(block_subsidy_test)
{
	ECC_Stop();
    const auto chainParams = CreateChainParams(MCBaseChainParams::MAIN);
	ECC_Start();
    TestBlockSubsidyHalvings(chainParams->GetConsensus()); // As in main
    TestBlockSubsidyHalvings(150); // As in regtest
    TestBlockSubsidyHalvings(1000); // Just another interval
}

BOOST_AUTO_TEST_CASE(subsidy_limit_test)
{
    const auto chainParams = CreateChainParams(MCBaseChainParams::MAIN);
    const Consensus::Params& consensus = chainParams->GetConsensus();
    MCAmount nSum = 0; 
    for (int nHeight = 0; nHeight < 560000000; nHeight += 10000) {
        MCAmount nSubsidy = GetBlockSubsidy(nHeight, consensus);
        MCAmount nTargetSubsidy = 85 * COIN;
        if (nHeight <= consensus.BigBoomHeight) {// next nHeight jump out of BigBoomHeight
            nTargetSubsidy += consensus.BigBoomValue;
            nSum += (nSubsidy- consensus.BigBoomValue) * 10000 + consensus.BigBoomValue * consensus.BigBoomHeight;// same as interval
        }
        else{
            nSum += nSubsidy * 10000;// same as interval
        }
        BOOST_CHECK(nSubsidy <= nTargetSubsidy);
        BOOST_CHECK(MoneyRange(nSum));
    }
    BOOST_CHECK_EQUAL(nSum, 402799999865600000ULL);
}

bool ReturnFalse() { return false; }
bool ReturnTrue() { return true; }

BOOST_AUTO_TEST_CASE(test_combiner_all)
{
    boost::signals2::signal<bool (), CombinerAll> Test;
    BOOST_CHECK(Test());
    Test.connect(&ReturnFalse);
    BOOST_CHECK(!Test());
    Test.connect(&ReturnTrue);
    BOOST_CHECK(!Test());
    Test.disconnect(&ReturnFalse);
    BOOST_CHECK(Test());
    Test.disconnect(&ReturnTrue);
    BOOST_CHECK(Test());
}
BOOST_AUTO_TEST_SUITE_END()
