// Copyright (c) 2011-2015 The Bitcoin Core developers
// Copyright (c) 2016-2019 The MagnaChain Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef MAGNACHAIN_QT_MAGNACHAINAMOUNTFIELD_H
#define MAGNACHAIN_QT_MAGNACHAINAMOUNTFIELD_H

#include "misc/amount.h"

#include <QWidget>

class AmountSpinBox;

QT_BEGIN_NAMESPACE
class QValueComboBox;
QT_END_NAMESPACE

/** Widget for entering magnachain amounts.
  */
class MagnaChainAmountField: public QWidget
{
    Q_OBJECT

    // ugly hack: for some unknown reason MCAmount (instead of qint64) does not work here as expected
    // discussion: https://github.com/magnachain/magnachain/pull/5117
    Q_PROPERTY(qint64 value READ value WRITE setValue NOTIFY valueChanged USER true)

public:
    explicit MagnaChainAmountField(QWidget *parent = 0);

    MCAmount value(bool *value=0) const;
    void setValue(const MCAmount& value);

    /** Set single step in satoshis **/
    void setSingleStep(const MCAmount& step);

    /** Make read-only **/
    void setReadOnly(bool fReadOnly);

    /** Mark current value as invalid in UI. */
    void setValid(bool valid);
    /** Perform input validation, mark field as invalid if entered value is not valid. */
    bool validate();

    /** Change unit used to display amount. */
    void setDisplayUnit(int unit);

    /** Make field empty and ready for new input. */
    void clear();

    /** Enable/Disable. */
    void setEnabled(bool fEnabled);

    /** Qt messes up the tab chain by default in some cases (issue https://bugreports.qt-project.org/browse/QTBUG-10907),
        in these cases we have to set it up manually.
    */
    QWidget *setupTabChain(QWidget *prev);

Q_SIGNALS:
    void valueChanged();

protected:
    /** Intercept focus-in event and ',' key presses */
    bool eventFilter(QObject *object, QEvent *event);

private:
    AmountSpinBox *amount;
    QValueComboBox *unit;

private Q_SLOTS:
    void unitChanged(int idx);

};

#endif // MAGNACHAIN_QT_MAGNACHAINAMOUNTFIELD_H
