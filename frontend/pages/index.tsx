/**
 * Partnership Tax Logic Engine - Main Dashboard
 */
import React, { useState } from 'react';
import Head from 'next/head';
import { 
  DocumentArrowUpIcon, 
  CalculatorIcon, 
  ChartBarIcon,
  CogIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface DashboardStats {
  totalPartnerships: number;
  activeDocuments: number;
  completedCalculations: number;
  complianceAlerts: number;
}

const Dashboard: React.FC = () => {
  const [stats] = useState<DashboardStats>({
    totalPartnerships: 12,
    activeDocuments: 8,
    completedCalculations: 45,
    complianceAlerts: 2
  });

  const quickActions = [
    {
      name: 'Upload Agreement',
      description: 'Parse a new partnership agreement',
      icon: DocumentArrowUpIcon,
      href: '/documents/upload',
      color: 'bg-blue-500'
    },
    {
      name: 'Calculate Allocations',
      description: 'Run target allocation analysis',
      icon: CalculatorIcon,
      href: '/calculations/allocations',
      color: 'bg-green-500'
    },
    {
      name: 'View Reports',
      description: 'Review compliance reports',
      icon: ChartBarIcon,
      href: '/reports',
      color: 'bg-purple-500'
    },
    {
      name: 'Settings',
      description: 'Configure integrations',
      icon: CogIcon,
      href: '/settings',
      color: 'bg-gray-500'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Partnership Tax Logic Engine - Dashboard</title>
        <meta name="description" content="AI-powered partnership tax automation platform" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-2xl font-bold text-gray-900">
                  Partnership Tax Logic Engine
                </h1>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">MVP v1.0.0</span>
              <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-600 font-medium text-sm">AD</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          
          {/* Compliance Alerts */}
          {stats.complianceAlerts > 0 && (
            <div className="mb-6 bg-yellow-50 border-l-4 border-yellow-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                </div>
                <div className="ml-3">
                  <p className="text-sm text-yellow-700">
                    You have {stats.complianceAlerts} compliance alerts requiring attention.
                    <a href="/compliance" className="font-medium underline text-yellow-700 hover:text-yellow-600 ml-1">
                      Review now →
                    </a>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">P</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Total Partnerships
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {stats.totalPartnerships}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <DocumentArrowUpIcon className="w-8 h-8 text-green-600" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Active Documents
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {stats.activeDocuments}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <CalculatorIcon className="w-8 h-8 text-purple-600" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Calculations Complete
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {stats.completedCalculations}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <ExclamationTriangleIcon className={`w-8 h-8 ${stats.complianceAlerts > 0 ? 'text-red-600' : 'text-green-600'}`} />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Compliance Status
                      </dt>
                      <dd className={`text-lg font-medium ${stats.complianceAlerts > 0 ? 'text-red-900' : 'text-green-900'}`}>
                        {stats.complianceAlerts > 0 ? `${stats.complianceAlerts} Alerts` : 'Compliant'}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="mb-8">
            <h2 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Quick Actions
            </h2>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {quickActions.map((action) => (
                <div
                  key={action.name}
                  className="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => {
                    // In a real app, this would use Next.js router
                    console.log(`Navigate to ${action.href}`);
                  }}
                >
                  <div className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className={`w-10 h-10 ${action.color} rounded-md flex items-center justify-center`}>
                          <action.icon className="w-6 h-6 text-white" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <h3 className="text-lg font-medium text-gray-900">
                          {action.name}
                        </h3>
                        <p className="text-sm text-gray-500">
                          {action.description}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Recent Activity
              </h3>
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <DocumentArrowUpIcon className="w-4 h-4 text-green-600" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      ABC Real Estate Partners agreement parsed
                    </p>
                    <p className="text-sm text-gray-500">
                      95% confidence, 4 partners identified
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-sm text-gray-500">
                    2 hours ago
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <CalculatorIcon className="w-4 h-4 text-blue-600" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      Target allocations calculated for XYZ Fund LP
                    </p>
                    <p className="text-sm text-gray-500">
                      Section 704(b) compliance verified
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-sm text-gray-500">
                    1 day ago
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <ChartBarIcon className="w-4 h-4 text-purple-600" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      Compliance report generated for DEF Holdings
                    </p>
                    <p className="text-sm text-gray-500">
                      Exported to CCH Axcess Tax
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-sm text-gray-500">
                    2 days ago
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* MVP Notice */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">i</span>
                </div>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  MVP Version 1.0
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <p>
                    This is the Minimum Viable Product version of the Partnership Tax Logic Engine. 
                    Core features include partnership agreement parsing, Section 704(b) capital account management, 
                    and target allocation calculations.
                  </p>
                  <p className="mt-2">
                    <strong>Next releases will include:</strong> Section 754 basis adjustments, 
                    integration APIs, advanced reporting, and pilot customer feedback implementations.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;