import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Modal,
  ScrollView,
} from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';
import {
  JanvaaniApi,
  SchemeSummary,
  SchemeDetail,
  EligibilityResult,
  ApiError,
} from '../api/client';
import { useAuth } from '../context/AuthContext';

interface Props {
  onBack: () => void;
}

// Safe formatters to prevent "Objects are not valid as a React child" crashes on release builds
const renderFormattedValue = (val: any): string => {
  if (val == null) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);
  if (typeof val === 'object') {
    if (val.description && typeof val.description === 'string') {
      const extra = [
        val.amount ? `₹${val.amount}` : null,
        val.frequency ? val.frequency : null,
      ].filter(Boolean).join(' • ');
      return extra ? `${val.description}\n(${extra})` : val.description;
    }
    return JSON.stringify(val, null, 2);
  }
  return String(val);
};

export default function SchemeDiscoveryScreen({ onBack }: Props) {
  const { profile, preferredLanguage, t } = useAuth();

  const [schemes, setSchemes] = useState<SchemeSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');

  // Scheme Detail Modal state
  const [selectedSchemeSlug, setSelectedSchemeSlug] = useState<string | null>(null);
  const [schemeDetail, setSchemeDetail] = useState<SchemeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Eligibility Evaluation State
  const [evalModalVisible, setEvalModalVisible] = useState<boolean>(false);
  const [evalScheme, setEvalScheme] = useState<SchemeSummary | null>(null);
  const [evalResult, setEvalResult] = useState<EligibilityResult | null>(null);
  const [evalLoading, setEvalLoading] = useState<boolean>(false);
  const [evalError, setEvalError] = useState<string | null>(null);

  const fetchSchemes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        ...(levelFilter !== 'all' ? { government_level: levelFilter } : {}),
        language: preferredLanguage || 'en',
      };
      const data = await JanvaaniApi.listSchemes(params);
      setSchemes(data);
    } catch (err: any) {
      const msg = err instanceof ApiError ? err.message : t('connectionError');
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [levelFilter, preferredLanguage, t]);

  useEffect(() => {
    fetchSchemes();
  }, [fetchSchemes]);

  // View scheme details
  const handleOpenDetail = async (slug: string) => {
    setSelectedSchemeSlug(slug);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const detail = await JanvaaniApi.getScheme(slug, preferredLanguage || 'en');
      setSchemeDetail(detail);
    } catch (err: any) {
      setDetailError(err?.message || 'Error loading scheme details');
    } finally {
      setDetailLoading(false);
    }
  };

  // Evaluate eligibility for a scheme
  const handleCheckEligibility = async (scheme: SchemeSummary) => {
    setEvalScheme(scheme);
    setEvalResult(null);
    setEvalError(null);
    setEvalModalVisible(true);
    setEvalLoading(true);

    try {
      // Build comprehensive citizen profile from authenticated citizen attributes + state/district
      const rawAttrs = profile?.attributes || {};
      const landHectares = rawAttrs.land_hectares != null && rawAttrs.land_hectares !== '' ? Number(rawAttrs.land_hectares) : undefined;
      const annualIncome = rawAttrs.annual_income != null && rawAttrs.annual_income !== '' ? Number(rawAttrs.annual_income) : undefined;
      const farmerCategory = rawAttrs.farmer_category || '';

      const isFarmer =
        rawAttrs.is_landholding_farmer !== undefined
          ? Boolean(rawAttrs.is_landholding_farmer)
          : (landHectares !== undefined && landHectares > 0) ||
            Boolean(farmerCategory && !farmerCategory.toLowerCase().includes('landless') && !farmerCategory.toLowerCase().includes('not'));

      const isTaxPayer =
        rawAttrs.is_income_tax_payer !== undefined
          ? Boolean(rawAttrs.is_income_tax_payer)
          : (annualIncome !== undefined ? annualIncome > 250000 : false);

      const citizenProfile: Record<string, any> = {
        ...rawAttrs,
        state: profile?.state || rawAttrs.state || 'Madhya Pradesh',
        district: profile?.district || rawAttrs.district || 'Sehore',
        land_hectares: landHectares,
        annual_income: annualIncome,
        is_landholding_farmer: isFarmer,
        is_income_tax_payer: isTaxPayer,
        is_institutional_landholder: rawAttrs.is_institutional_landholder ?? false,
        is_serving_or_retired_govt_employee: rawAttrs.is_serving_or_retired_govt_employee ?? rawAttrs.is_govt_employee ?? false,
        is_govt_employee: rawAttrs.is_govt_employee ?? false,
        monthly_pension: rawAttrs.monthly_pension ?? 0,
        is_constitutional_post_holder: rawAttrs.is_constitutional_post_holder ?? false,
        has_savings_bank_account: rawAttrs.has_savings_bank_account ?? true,
      };

      let result: EligibilityResult;
      try {
        // 1. Try production reviewed scheme evaluation against database rules
        result = await JanvaaniApi.evaluateReviewedScheme({
          scheme_id: scheme.slug,
          profile: citizenProfile,
          language: preferredLanguage || 'en',
        });
      } catch (err: any) {
        // 2. Fallback to dynamic client-side rule evaluation if reviewed criteria lookup unavailable
        const isCentral = scheme.government_level === 'central';
        result = await JanvaaniApi.evaluateEligibility({
          scheme_id: scheme.slug,
          scheme_name: scheme.title,
          rule_version: 'v1',
          rules: [
            {
              rule_id: 'jurisdiction_state',
              field: 'state',
              operator: isCentral ? 'exists' : 'in',
              expected: isCentral ? 'present' : [citizenProfile.state],
              explanation: isCentral
                ? 'Central scheme applicable across all Indian States & UTs'
                : `Applicable to jurisdiction: ${citizenProfile.state}`,
              supported: true,
              required: true,
            },
            {
              rule_id: 'landholding_farmer_check',
              field: 'is_landholding_farmer',
              operator: 'eq',
              expected: true,
              explanation: 'Applicant must be an agricultural landholding farmer',
              supported: true,
              required: true,
            },
            {
              rule_id: 'income_tax_exclusion',
              field: 'is_income_tax_payer',
              operator: 'eq',
              expected: false,
              explanation: 'Exclusion: Income tax payers are not eligible',
              supported: true,
              required: true,
            },
          ],
          profile: citizenProfile,
          language: preferredLanguage || 'en',
        });
      }

      setEvalResult(result);
    } catch (err: any) {
      setEvalError(err?.message || 'Eligibility evaluation failed');
    } finally {
      setEvalLoading(false);
    }
  };

  // Filter schemes locally by search query
  const filteredSchemes = schemes.filter(
    (s) =>
      s.title.toLowerCase().includes(query.toLowerCase()) ||
      s.administering_authority.toLowerCase().includes(query.toLowerCase()) ||
      (s.versions[0]?.description || '').toLowerCase().includes(query.toLowerCase())
  );

  return (
    <View style={styles.container}>
      {/* Top Bar Header with Back Button & Logo */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>{t('schemesHeaderTitle')}</Text>
          <Text style={styles.headerSub}>{t('schemesHeaderSub')}</Text>
        </View>
        <TouchableOpacity style={styles.refreshBtn} onPress={fetchSchemes}>
          <Ionicons name="refresh" size={20} color={Colors.primaryForest} />
        </TouchableOpacity>
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterRow}>
        <TouchableOpacity
          style={[styles.filterChip, levelFilter === 'all' && styles.filterChipActive]}
          onPress={() => setLevelFilter('all')}
        >
          <Text style={[styles.filterText, levelFilter === 'all' && styles.filterTextActive]}>
            {t('filterAll')}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterChip, levelFilter === 'central' && styles.filterChipActive]}
          onPress={() => setLevelFilter('central')}
        >
          <Text style={[styles.filterText, levelFilter === 'central' && styles.filterTextActive]}>
            {t('filterCentral')}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterChip, levelFilter === 'state' && styles.filterChipActive]}
          onPress={() => setLevelFilter('state')}
        >
          <Text style={[styles.filterText, levelFilter === 'state' && styles.filterTextActive]}>
            {t('filterState')}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Search Header */}
      <View style={styles.searchContainer}>
        <Ionicons name="search-outline" size={20} color={Colors.secondaryText} />
        <TextInput
          style={styles.searchInput}
          placeholder={t('searchSchemesPlaceholder')}
          value={query}
          onChangeText={setQuery}
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => setQuery('')}>
            <Ionicons name="close-circle" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>
        )}
      </View>

      {/* Loading & Error States */}
      {loading && (
        <View style={styles.centerBox}>
          <ActivityIndicator size="large" color={Colors.primaryForest} />
          <Text style={styles.statusText}>{t('loadingSchemes')}</Text>
        </View>
      )}

      {error && !loading && (
        <View style={styles.errorBox}>
          <Ionicons name="alert-circle-outline" size={32} color={Colors.error} />
          <Text style={styles.errorTitle}>{t('connectionError')}</Text>
          <Text style={styles.errorMsg}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={fetchSchemes}>
            <Text style={styles.retryText}>{t('retry')}</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Scheme List */}
      {!loading && !error && (
        <FlatList
          data={filteredSchemes}
          keyExtractor={(item) => item.slug}
          contentContainerStyle={{ paddingBottom: 30 }}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.authority}>{item.administering_authority}</Text>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>
                    {item.government_level === 'central' ? t('centralBadge') : t('stateBadge')}
                  </Text>
                </View>
              </View>

              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.desc}>
                {renderFormattedValue(item.versions[0]?.description || '')}
              </Text>

              <View style={styles.cardFooter}>
                <TouchableOpacity
                  style={styles.detailBtn}
                  onPress={() => handleOpenDetail(item.slug)}
                >
                  <Text style={styles.detailBtnText}>{t('viewDetails')}</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.actionBtn}
                  onPress={() => handleCheckEligibility(item)}
                >
                  <Ionicons name="checkmark-done" size={14} color={Colors.white} />
                  <Text style={styles.actionBtnText}>{t('checkEligibility')}</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Ionicons name="search" size={40} color={Colors.secondaryText} />
              <Text style={styles.emptyTitle}>{t('noSchemesTitle')}</Text>
              <Text style={styles.emptyText}>
                {t('noSchemesSub')}
              </Text>
            </View>
          }
        />
      )}

      {/* Scheme Details Modal */}
      <Modal visible={!!selectedSchemeSlug} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle} numberOfLines={1}>
                {schemeDetail?.title || t('schemeDetailsTitle')}
              </Text>
              <TouchableOpacity onPress={() => setSelectedSchemeSlug(null)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            {detailLoading && (
              <View style={styles.centerBox}>
                <ActivityIndicator color={Colors.primaryForest} />
              </View>
            )}

            {detailError && <Text style={styles.errorMsg}>{detailError}</Text>}

            {schemeDetail && !detailLoading && (
              <ScrollView style={{ padding: 16 }}>
                <Text style={styles.detailSectionTitle}>{t('adminAuthority')}</Text>
                <Text style={styles.detailText}>{schemeDetail.administering_authority}</Text>

                <Text style={styles.detailSectionTitle}>{t('schemeLevel')}</Text>
                <Text style={styles.detailText}>
                  {schemeDetail.government_level === 'central'
                    ? t('centralBadge')
                    : schemeDetail.government_level === 'state'
                    ? t('stateBadge')
                    : schemeDetail.government_level}
                </Text>

                {schemeDetail.versions[0] && (
                  <>
                    <Text style={styles.detailSectionTitle}>{t('schemeObjective')}</Text>
                    <Text style={styles.detailText}>
                      {renderFormattedValue(schemeDetail.versions[0].description)}
                    </Text>

                    <Text style={styles.detailSectionTitle}>{t('benefits')}</Text>
                    {(() => {
                      const b = schemeDetail.versions[0].benefits as any;
                      if (!b) return null;
                      if (typeof b === 'string') {
                        return <Text style={styles.detailText}>{b}</Text>;
                      }
                      const benefitList = Array.isArray(b) ? b : [b];
                      return benefitList.map((item: any, bIdx: number) => {
                        if (typeof item === 'string') {
                          return <Text key={bIdx} style={styles.bulletItem}>• {item}</Text>;
                        }
                        if (typeof item === 'object' && item !== null) {
                          const amount = item.amount ? `₹${item.amount}` : null;
                          const freq = item.frequency ? String(item.frequency).toUpperCase() : null;
                          const desc = item.description || '';
                          const conditions = Array.isArray(item.conditions) ? item.conditions : [];
                          return (
                            <View key={bIdx} style={{ gap: 6, marginBottom: 8 }}>
                              {(amount || freq) && (
                                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#ECFDF5', padding: 8, borderRadius: 8 }}>
                                  <Ionicons name="cash-outline" size={16} color="#059669" />
                                  <Text style={{ fontSize: 13, fontWeight: '700', color: '#065F46' }}>
                                    {[amount, freq].filter(Boolean).join(' • ')}
                                  </Text>
                                </View>
                              )}
                              {desc ? <Text style={styles.detailText}>{desc}</Text> : null}
                              {conditions.length > 0 && (
                                <View style={{ marginTop: 4 }}>
                                  <Text style={{ fontSize: 12, fontWeight: '600', color: Colors.secondaryText, marginBottom: 2 }}>{t('eligibilityConditionsLabel')}</Text>
                                  {conditions.map((c: any, idx: number) => (
                                    <Text key={idx} style={styles.bulletItem}>
                                      • {typeof c === 'string' ? c : JSON.stringify(c)}
                                    </Text>
                                  ))}
                                </View>
                              )}
                            </View>
                          );
                        }
                        return <Text key={bIdx} style={styles.detailText}>{String(item)}</Text>;
                      });
                    })()}

                    <Text style={styles.detailSectionTitle}>{t('requiredDocs')}</Text>
                    {(() => {
                      const docs = schemeDetail.versions[0].required_documents as any;
                      if (!docs || !Array.isArray(docs) || docs.length === 0) {
                        return <Text style={styles.detailText}>{t('noDocsListed')}</Text>;
                      }
                      return docs.map((doc: any, idx: number) => {
                        if (typeof doc === 'string') {
                          return <Text key={idx} style={styles.bulletItem}>• {doc}</Text>;
                        }
                        if (typeof doc === 'object' && doc !== null) {
                          const docName = doc.name || doc.document_type || doc.title || JSON.stringify(doc);
                          const condition = doc.condition ? ` (${doc.condition})` : '';
                          return (
                            <Text key={idx} style={styles.bulletItem}>
                              • <Text style={{ fontWeight: '600' }}>{docName}</Text>{condition}
                            </Text>
                          );
                        }
                        return <Text key={idx} style={styles.bulletItem}>• {String(doc)}</Text>;
                      });
                    })()}

                    <Text style={styles.detailSectionTitle}>{t('applicationProcess')}</Text>
                    {(() => {
                      const proc = schemeDetail.versions[0].application_process as any;
                      if (!proc) return null;
                      if (typeof proc === 'string') {
                        return <Text style={styles.detailText}>{proc}</Text>;
                      }
                      if (Array.isArray(proc)) {
                        return proc.map((step: any, idx: number) => {
                          if (typeof step === 'string') {
                            return <Text key={idx} style={styles.bulletItem}>{idx + 1}. {step}</Text>;
                          }
                          if (typeof step === 'object' && step !== null) {
                            const stepNum = step.step || idx + 1;
                            const desc = step.description || step.title || JSON.stringify(step);
                            const url = step.url ? `\n   ${t('portalLabel')}: ${step.url}` : '';
                            return (
                              <Text key={idx} style={[styles.bulletItem, { marginBottom: 6 }]}>
                                <Text style={{ fontWeight: '700' }}>{t('stepLabel')} {stepNum}: </Text>
                                {desc}{url}
                              </Text>
                            );
                          }
                          return <Text key={idx} style={styles.bulletItem}>{String(step)}</Text>;
                        });
                      }
                      return <Text style={styles.detailText}>{JSON.stringify(proc, null, 2)}</Text>;
                    })()}
                  </>
                )}
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>

      {/* Eligibility Modal */}
      <Modal visible={evalModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle} numberOfLines={1}>
                {t('eligibilityModalTitle')}: {evalScheme?.title}
              </Text>
              <TouchableOpacity onPress={() => setEvalModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <ScrollView style={{ padding: 16 }}>
              {evalLoading && (
                <View style={styles.centerBox}>
                  <ActivityIndicator size="large" color={Colors.primaryForest} />
                  <Text style={styles.statusText}>{t('evaluatingCriteria')}</Text>
                </View>
              )}

              {evalError && <Text style={styles.errorMsg}>{evalError}</Text>}

              {evalResult && !evalLoading && (
                <View>
                  {/* Distinct Status Banners */}
                  {evalResult.status === 'ELIGIBLE' && (
                    <View style={[styles.resultBanner, styles.eligibleBanner]}>
                      <Ionicons name="checkmark-circle" size={24} color="#15803D" />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.resultTitleGreen}>{t('eligibleTitle')}</Text>
                        <Text style={styles.resultSubGreen}>{t('eligibleSub')}</Text>
                      </View>
                    </View>
                  )}

                  {evalResult.status === 'NOT_ELIGIBLE' && (
                    <View style={[styles.resultBanner, styles.notEligibleBanner]}>
                      <Ionicons name="close-circle" size={24} color={Colors.error} />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.resultTitleRed}>{t('notEligibleTitle')}</Text>
                        <Text style={styles.resultSubRed}>{t('notEligibleSub')}</Text>
                      </View>
                    </View>
                  )}

                  {evalResult.status === 'INSUFFICIENT_INFORMATION' && (
                    <View style={[styles.resultBanner, styles.uncertainBanner]}>
                      <Ionicons name="help-circle" size={24} color="#D97706" />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.resultTitleAmber}>{t('insufficientTitle')}</Text>
                        <Text style={styles.resultSubAmber}>
                          {t('insufficientSub')}
                        </Text>
                      </View>
                    </View>
                  )}

                  {/* Summary Note */}
                  <Text style={styles.evalSummary}>{evalResult.summary}</Text>

                  {/* Missing Fields Requirement */}
                  {((evalResult.missing_fields && evalResult.missing_fields.length > 0) ||
                    evalResult.conditions.some((c) => (c as any).status === 'MISSING')) && (
                    <View style={styles.missingCard}>
                      <Text style={styles.missingTitle}>{t('missingFieldsTitle')}</Text>
                      {(evalResult.missing_fields && evalResult.missing_fields.length > 0
                        ? evalResult.missing_fields
                        : evalResult.conditions
                            .filter((c) => (c as any).status === 'MISSING')
                            .map((c) => c.field)
                      ).map((f, i) => (
                        <Text key={i} style={styles.missingItem}>
                          ⚠️ {f.replace(/_/g, ' ')}: {t('missingFromProfile')}
                        </Text>
                      ))}
                      <TouchableOpacity
                        style={styles.missingUpdateBtn}
                        onPress={() => {
                          setEvalModalVisible(false);
                          onBack();
                        }}
                      >
                        <Ionicons name="create-outline" size={14} color="#B45309" />
                        <Text style={styles.missingUpdateBtnText}>{t('editProfileBtn')}</Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  {/* Criteria Condition Details */}
                  <Text style={styles.detailSectionTitle}>{t('criteriaRulesTitle')}</Text>
                  {evalResult.conditions.map((cond, idx) => {
                    const isPass = cond.satisfied === true || (cond as any).status === 'PASS';
                    const isFail = cond.satisfied === false || (cond as any).status === 'FAIL';
                    const isMissing = !isPass && !isFail;

                    return (
                      <View key={idx} style={styles.conditionCard}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                          <Ionicons
                            name={
                              isPass
                                ? 'checkmark-circle'
                                : isFail
                                ? 'close-circle'
                                : 'alert-circle'
                            }
                            size={18}
                            color={
                              isPass
                                ? '#15803D'
                                : isFail
                                ? Colors.error
                                : '#D97706'
                            }
                          />
                          <Text style={styles.condField}>
                            {cond.field.replace(/_/g, ' ')} {cond.operator ? `(${cond.operator} ${String(cond.expected)})` : ''}
                          </Text>
                        </View>
                        <Text style={styles.condExplanation}>{cond.explanation}</Text>
                        <Text
                          style={[
                            styles.condStatus,
                            isPass && { color: '#15803D' },
                            isFail && { color: Colors.error },
                            isMissing && { color: '#D97706' },
                          ]}
                        >
                          {isPass
                            ? t('ruleStatusSatisfied')
                            : isFail
                            ? t('ruleStatusFailed')
                            : t('ruleStatusMissing')}
                        </Text>
                      </View>
                    );
                  })}
                </View>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.softCream, padding: 16 },
  topHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  backBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: Colors.white,
    elevation: 2,
  },
  refreshBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: '#F0FDF4',
  },
  logo: {
    width: 32,
    height: 32,
    resizeMode: 'contain',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: 'bold',
    color: Colors.primaryText,
  },
  headerSub: {
    fontSize: 11,
    color: Colors.secondaryText,
  },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  filterChip: {
    backgroundColor: Colors.white,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  filterChipActive: {
    backgroundColor: Colors.primaryForest,
    borderColor: Colors.primaryForest,
  },
  filterText: {
    fontSize: 12,
    color: Colors.primaryText,
    fontWeight: '500',
  },
  filterTextActive: {
    color: Colors.white,
    fontWeight: 'bold',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    paddingHorizontal: 12,
    borderRadius: 12,
    height: 48,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  searchInput: { flex: 1, marginLeft: 8, fontSize: 14 },
  centerBox: { alignItems: 'center', padding: 24 },
  statusText: { fontSize: 13, color: Colors.secondaryText, marginTop: 8 },
  errorBox: {
    backgroundColor: '#FEE2E2',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 16,
  },
  errorTitle: { fontSize: 14, fontWeight: 'bold', color: Colors.error, marginTop: 4 },
  errorMsg: { fontSize: 12, color: Colors.error, textAlign: 'center', marginTop: 4 },
  retryBtn: {
    marginTop: 10,
    backgroundColor: Colors.error,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 8,
  },
  retryText: { color: Colors.white, fontWeight: 'bold', fontSize: 12 },
  card: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  authority: { fontSize: 11, color: Colors.secondaryText, flex: 1 },
  badge: { backgroundColor: '#DCFCE7', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  badgeText: { fontSize: 10, color: Colors.primaryForest, fontWeight: 'bold' },
  title: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText, marginTop: 4 },
  desc: { fontSize: 13, color: Colors.primaryText, lineHeight: 18, marginTop: 4, marginBottom: 12 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  detailBtn: { paddingVertical: 6 },
  detailBtnText: { color: Colors.secondaryText, fontSize: 12, fontWeight: 'bold' },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.primaryForest,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  actionBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 12 },
  emptyContainer: { alignItems: 'center', marginTop: 32, paddingHorizontal: 20 },
  emptyTitle: { fontSize: 15, fontWeight: 'bold', color: Colors.primaryText, marginTop: 8 },
  emptyText: { fontSize: 12, color: Colors.secondaryText, textAlign: 'center', marginTop: 4, lineHeight: 18 },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '85%',
    paddingBottom: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText, flex: 1, marginRight: 8 },
  detailSectionTitle: { fontSize: 13, fontWeight: 'bold', color: Colors.primaryForest, marginTop: 12, marginBottom: 4 },
  detailText: { fontSize: 13, color: Colors.primaryText, lineHeight: 18 },
  bulletItem: { fontSize: 13, color: Colors.primaryText, marginLeft: 8, marginVertical: 2 },
  resultBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: 12,
    marginBottom: 12,
  },
  eligibleBanner: { backgroundColor: '#DCFCE7', borderWidth: 1, borderColor: '#86EFAC' },
  notEligibleBanner: { backgroundColor: '#FEE2E2', borderWidth: 1, borderColor: '#FCA5A5' },
  uncertainBanner: { backgroundColor: '#FEF3C7', borderWidth: 1, borderColor: '#FCD34D' },
  resultTitleGreen: { fontSize: 15, fontWeight: 'bold', color: '#15803D' },
  resultSubGreen: { fontSize: 11, color: '#166534', marginTop: 2 },
  resultTitleRed: { fontSize: 15, fontWeight: 'bold', color: Colors.error },
  resultSubRed: { fontSize: 11, color: '#991B1B', marginTop: 2 },
  resultTitleAmber: { fontSize: 15, fontWeight: 'bold', color: '#B45309' },
  resultSubAmber: { fontSize: 11, color: '#92400E', marginTop: 2 },
  evalSummary: { fontSize: 13, color: Colors.primaryText, marginBottom: 12, lineHeight: 18 },
  missingCard: {
    backgroundColor: '#FFFBEB',
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  missingTitle: { fontSize: 12, fontWeight: 'bold', color: '#B45309', marginBottom: 6 },
  missingItem: { fontSize: 12, color: '#92400E', marginVertical: 2 },
  missingUpdateBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
    alignSelf: 'flex-start',
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  missingUpdateBtnText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#92400E',
  },
  conditionCard: {
    backgroundColor: '#F8FAFC',
    padding: 10,
    borderRadius: 8,
    marginVertical: 4,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  condField: { fontSize: 12, fontWeight: 'bold', color: Colors.primaryText },
  condExplanation: { fontSize: 11, color: Colors.secondaryText, marginTop: 2 },
  condStatus: { fontSize: 11, fontWeight: '500', color: Colors.primaryForest, marginTop: 4 },
});