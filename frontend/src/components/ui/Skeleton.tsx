import { Card } from "./index";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-linen rounded animate-pulse ${className}`} />;
}

export function DashboardSkeleton() {
  return (
    <div>
      <Skeleton className="h-8 w-64 mb-2" />
      <Skeleton className="h-4 w-96 mb-8" />
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <Skeleton className="h-20" />
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} padding="sm">
            <Skeleton className="h-12" />
          </Card>
        ))}
      </div>
      <Card>
        <Skeleton className="h-48" />
      </Card>
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function RunDetailSkeleton() {
  return (
    <div className="grid grid-cols-5 gap-6">
      <div className="col-span-2">
        <Card>
          <Skeleton className="h-64 w-full" />
        </Card>
      </div>
      <div className="col-span-3 space-y-4">
        <Card>
          <Skeleton className="h-32 w-full" />
        </Card>
        <Card>
          <Skeleton className="h-24 w-full" />
        </Card>
        <Card>
          <Skeleton className="h-24 w-full" />
        </Card>
      </div>
    </div>
  );
}

export function BatchDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-48" />
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} padding="sm">
            <Skeleton className="h-10" />
          </Card>
        ))}
      </div>
      <Skeleton className="h-4 w-full" />
      <TableSkeleton rows={5} />
    </div>
  );
}

export function FormSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-2/3" />
    </div>
  );
}
