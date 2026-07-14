import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => (
  <div
    className={`animate-pulse rounded-md bg-muted ${className}`}
    aria-hidden="true"
  />
);

/** A KPI card skeleton matching the dashboard card layout */
export const SkeletonCard: React.FC = () => (
  <div className="bg-card p-6 rounded-lg shadow-stripe border border-border space-y-3">
    <Skeleton className="h-4 w-24" />
    <Skeleton className="h-8 w-32" />
  </div>
);

/** A chart skeleton with a title bar and a grey rectangle */
export const SkeletonChart: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-card p-6 rounded-lg shadow-stripe border border-border ${className}`}>
    <Skeleton className="h-5 w-40 mb-4" />
    <Skeleton className="h-64 sm:h-80 w-full rounded-lg" />
  </div>
);
